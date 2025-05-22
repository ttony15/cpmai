# decision_report_generator.py – W4 Decision Report Generator with Persisted Writer’s Mode
# ======================================================================

## Purpose
# Generates final decision report PDFs with a user-specific "Writer's Mode"
# (executive vs instructional) that persists across sessions.

from __future__ import annotations
import io
import json
import logging
import os
import subprocess
from typing import Any, Dict, Optional

import boto3
import psycopg2
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from jose import jwk, jwt as jose_jwt
from psycopg2.extras import RealDictCursor
import requests

# ---------------------------------------------------------------------------
## CONFIGURATION & CLIENTS
# ---------------------------------------------------------------------------
DB_SECRET_ID = os.environ["DB_SECRET_ID"]
JWKS_URL = os.environ["JWKS_URL"]
REPORT_BUCKET = os.environ.get("REPORT_BUCKET")  # S3 bucket for PDFs
LATEX_TEMPLATE_DIR = os.environ.get("LATEX_TEMPLATE_DIR", "/templates")

# AWS clients
ssm = boto3.client("secretsmanager")
s3 = boto3.client("s3")

# Postgres connection
# Assumes a table user_preferences(user_id PK, writer_mode TEXT)
db_cfg = json.loads(ssm.get_secret_value(SecretId=DB_SECRET_ID)["SecretString"])
conn = psycopg2.connect(**db_cfg, sslmode="require", cursor_factory=RealDictCursor)
conn.autocommit = True

# JWT verification via JWKS
jwks = requests.get(JWKS_URL, timeout=3).json()
key_set = {k["kid"]: k for k in jwks["keys"]}

app = FastAPI(title="Decision Report Generator", version="0.2")


# ---------------------------------------------------------------------------
## AUTHENTICATION
# ---------------------------------------------------------------------------
def verify_jwt(
    token: str = Depends(lambda req: req.headers.get("Authorization", " ").split()[-1]),
):
    """Validate JWT via JWKS"""
    if not token:
        raise HTTPException(401, "Missing bearer token")
    header = jose_jwt.get_unverified_header(token)
    key_data = key_set.get(header["kid"])
    if not key_data:
        raise HTTPException(401, "Invalid token key ID")
    key = jwk.construct(key_data)
    payload = jose_jwt.decode(token, key.to_dict(), algorithms=[header["alg"]])
    return payload  # contains 'sub' as user_id


# ---------------------------------------------------------------------------
## USER PREFERENCES HELPERS
# ---------------------------------------------------------------------------
def fetch_writer_mode(user_id: str) -> Optional[str]:
    """Load the persisted writer_mode for this user, if any."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT writer_mode FROM user_preferences WHERE user_id=%s", (user_id,)
        )
        row = cur.fetchone()
        return row["writer_mode"] if row else None


def persist_writer_mode(user_id: str, mode: str) -> None:
    """Insert or update the user's writer_mode preference."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO user_preferences(user_id, writer_mode) VALUES(%s,%s)"
            " ON CONFLICT(user_id) DO UPDATE SET writer_mode=EXCLUDED.writer_mode",
            (user_id, mode),
        )


# ---------------------------------------------------------------------------
## DATA FETCH
# ---------------------------------------------------------------------------
def fetch_report_data(project_id: str) -> Dict[str, Any]:
    """Retrieve quotes, scopes, budget, and risk data from Postgres."""
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM projects WHERE id=%s", (project_id,))
        proj = cur.fetchone()
        if not proj:
            raise HTTPException(404, "Project not found")
        data: Dict[str, Any] = {"project_name": proj["name"]}

        cur.execute("SELECT * FROM quotes WHERE project_id=%s", (project_id,))
        data["quotes"] = cur.fetchall()

        cur.execute(
            "SELECT trade, scope_json FROM trade_scopes WHERE project_id=%s",
            (project_id,),
        )
        data["scopes"] = cur.fetchall()

        cur.execute(
            "SELECT budget_json FROM optimal_budget WHERE project_id=%s", (project_id,)
        )
        row = cur.fetchone()
        data["budget"] = row["budget_json"] if row else {}

        cur.execute(
            "SELECT risk_score FROM risk_scoring WHERE project_id=%s", (project_id,)
        )
        data["risks"] = cur.fetchall()
    return data


# ---------------------------------------------------------------------------
## TONE-BASED PROMPT TEMPLATES
# ---------------------------------------------------------------------------
PROMPT_TEMPLATES = {
    "executive": (
        "You are writing an executive summary for senior leadership. "
        "Highlight key vendor selections, costs, and high-level risks."
    ),
    "instructional": (
        "You are writing step-by-step instructions for the project team. "
        "Justify each vendor choice with detailed 'you would...' style guidance."
    ),
}


# ---------------------------------------------------------------------------
## PDF RENDERING FLOW
# ---------------------------------------------------------------------------
def render_pdf(data: Dict[str, Any], tone: str) -> bytes:
    """
    1. Populate LaTeX template with data + tone-driven GPT summaries
    2. Run `pdflatex` to generate PDF bytes
    """
    # 1) Narrative via LLM
    system = PROMPT_TEMPLATES[tone]
    user_msg = json.dumps(
        {
            "quotes": data["quotes"],
            "scopes": data["scopes"],
            "budget": data["budget"],
            "risks": data["risks"],
        }
    )
    resp = openai.chat.completions.create(
        model="gpt-4o-128k",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        temperature=0,
    )
    narrative = resp.choices[0].message.content

    # 2) Fill LaTeX
    tex = open(f"{LATEX_TEMPLATE_DIR}/report.tex", "r").read()
    tex_filled = tex.replace("{{PROJECT_NAME}}", data["project_name"])
    tex_filled = tex_filled.replace("{{NARRATIVE}}", narrative)

    # Write + compile
    tmpdir = "/tmp"
    path = os.path.join(tmpdir, "report.tex")
    with open(path, "w") as f:
        f.write(tex_filled)
    subprocess.run(["pdflatex", "-output-directory", tmpdir, path], check=True)
    pdf_path = os.path.join(tmpdir, "report.pdf")
    with open(pdf_path, "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
## /generate-report ENDPOINT
# ---------------------------------------------------------------------------
@app.post("/generate-report")
async def generate_report(
    project_id: str = Query(...),
    tone: Optional[str] = Query(None, regex="^(executive|instructional)$"),
    auth: Any = Depends(verify_jwt),
):
    """
    Generate the final decision report PDF, respecting a persisted writer_mode.

    If `tone` is passed, override and save it; otherwise load the user's
    last-saved writer_mode (defaulting to 'executive').
    """
    user_id = auth["sub"]
    # Determine tone
    if tone:
        selected = tone
        persist_writer_mode(user_id, selected)
    else:
        stored = fetch_writer_mode(user_id)
        selected = stored if stored in PROMPT_TEMPLATES else "executive"

    # Fetch data + render
    data = fetch_report_data(project_id)
    pdf_bytes = render_pdf(data, selected)

    # Optionally upload
    if REPORT_BUCKET:
        key = f"reports/{project_id}_{selected}.pdf"
        s3.put_object(Bucket=REPORT_BUCKET, Key=key, Body=pdf_bytes)

    # Return file
    outfile = f"/tmp/report.pdf"
    with open(outfile, "wb") as f:
        f.write(pdf_bytes)
    return FileResponse(
        path=outfile,
        media_type="application/pdf",
        filename=f"{project_id}_{selected}_report.pdf",
    )
