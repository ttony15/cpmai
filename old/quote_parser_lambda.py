"""quote_parser_lambda.py – Dual‑Model Verified Parsing (v2)
==========================================================
This version eliminates silent hallucinations by running **two independent
models** on every quote PDF and reconciling the JSON outputs.

Workflow
--------
1. **Primary parse**  – GPT‑4o‑128k function‑calling JSON.
2. **Checker parse**  – Claude 3 Sonnet (cheaper, different vendor).
3. **Diff**           – Keys `vendor, trade, price` must match *exactly* after
   normalisation. Scope bullet lists compared with RapidFuzz ≥ 90 %.
4. **On mismatch**    – Push the PDF key + both JSON blobs into
   `quote_review_queue` (SQS) and **skip DB insert** so a human can decide.
5. **On match**       – Insert single row (primary JSON) into Aurora, archive
the PDF.

Environment additions
---------------------
```
CHECK_MODEL="claude-3-sonnet-20240229"
REVIEW_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123/quote_review_queue
SENSITIVITY=normal|pii
```

Dependencies update
-------------------
anthropic>=0.21.4
rapidfuzz>=3.6.0

"""

from __future__ import annotations
import io, json, logging, os, re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

import boto3, openai, pdfplumber, psycopg2
from rapidfuzz.fuzz import token_sort_ratio
from psycopg2.extras import execute_values
import anthropic

# --------------------------- CONFIG --------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

SECRET_ID = os.environ["SECRET_ID"]
DB_SECRET_ID = os.environ["DB_SECRET_ID"]
SHEET_TABLE = os.environ.get("SHEET_TABLE", "quotes")
PRIMARY_MODEL = os.environ.get("GPT_MODEL", "gpt-4o-128k")
CHECK_MODEL = os.environ.get("CHECK_MODEL", "claude-3-sonnet-20240229")
REVIEW_QUEUE_URL = os.environ["REVIEW_QUEUE_URL"]
SENSITIVITY = os.environ.get("SENSITIVITY", "normal")

ssm = boto3.client("secretsmanager")
secrets = lambda sid: json.loads(ssm.get_secret_value(SecretId=sid)["SecretString"])
openai.api_key = secrets(SECRET_ID)["OPENAI_API_KEY"]
claude_key = secrets(SECRET_ID).get("ANTHROPIC_API_KEY")  # same secret bundle

a_client = anthropic.Client(api_key=claude_key)

# DB
cfg = secrets(DB_SECRET_ID)
conn = psycopg2.connect(**cfg, sslmode="require")
conn.autocommit = True

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# ----------------------- HELPERS -----------------------------------------


def extract_text(blob: bytes) -> str:
    with pdfplumber.open(io.BytesIO(blob)) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


def normalise_price(p) -> Decimal | None:
    if p is None:
        return None
    cleaned = re.sub(r"[^0-9.]+", "", str(p))
    return Decimal(cleaned) if cleaned else None


def call_openai(text: str) -> dict:
    prompt = "You are an estimator… (same as before)"
    resp = openai.chat.completions.create(
        model=PRIMARY_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text[:12000]},
        ],
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)


def call_claude(text: str) -> dict:
    prompt = (
        "Return JSON vendor, trade, price, scope (list), inclusions, exclusions, terms."
    )
    msg = a_client.messages.create(
        model=CHECK_MODEL,
        max_tokens=512,
        temperature=0,
        system="You are a checker.",
        messages=[{"role": "user", "content": text[:12000]}],
    )
    return json.loads(msg.content[0].text)


def rows_equal(a: dict, b: dict) -> bool:
    if a.get("vendor", "").strip().lower() != b.get("vendor", "").strip().lower():
        return False
    if a.get("trade", "").strip().lower() != b.get("trade", "").strip().lower():
        return False
    if normalise_price(a.get("price")) != normalise_price(b.get("price")):
        return False
    # scopes similarity
    sim = token_sort_ratio(" ".join(a.get("scope", [])), " ".join(b.get("scope", [])))
    return sim >= 90


def queue_for_review(bucket: str, key: str, prim: dict, check: dict):
    sqs.send_message(
        QueueUrl=REVIEW_QUEUE_URL,
        MessageBody=json.dumps(
            {"bucket": bucket, "key": key, "primary": prim, "check": check}
        ),
        MessageGroupId="quote",
        MessageDeduplicationId=key,
    )


# ----------------------- CORE --------------------------------------------


def insert_rows(rows: List[Dict[str, Any]]):
    sql = f"INSERT INTO {SHEET_TABLE}(etag, uploaded_at, vendor, trade, price, scope,inclusions,exclusions,terms) VALUES %s ON CONFLICT(etag) DO NOTHING"
    vals = [
        (
            r["etag"],
            r["uploaded_at"],
            r["vendor"],
            r["trade"],
            r["price"],
            json.dumps(r["scope"]),
            json.dumps(r["inclusions"]),
            json.dumps(r["exclusions"]),
            r["terms"],
        )
        for r in rows
    ]
    with conn.cursor() as cur:
        execute_values(cur, sql, vals)


# ----------------------- HANDLER -----------------------------------------


def lambda_handler(event, _):
    inserted = 0
    for rec in event.get("Records", []):
        bucket, key, etag = (
            rec["s3"]["bucket"]["name"],
            rec["s3"]["object"]["key"],
            rec["s3"]["object"]["eTag"],
        )
        logger.info("Quote %s", key)
        # skip dup
        with conn.cursor() as cur:
            cur.execute(f"SELECT 1 FROM {SHEET_TABLE} WHERE etag=%s", (etag,))
            if cur.fetchone():
                continue
        blob = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        text = extract_text(blob)
        primary = call_openai(text)
        checker = call_claude(text)
        if not rows_equal(primary, checker):
            logger.warning("Mismatch on %s queued for review", key)
            queue_for_review(bucket, key, primary, checker)
            continue
        row = {
            "etag": etag,
            "uploaded_at": datetime.utcnow(),
            "vendor": primary.get("vendor"),
            "trade": primary.get("trade"),
            "price": normalise_price(primary.get("price")),
            "scope": primary.get("scope", []),
            "inclusions": primary.get("inclusions", []),
            "exclusions": primary.get("exclusions", []),
            "terms": primary.get("terms"),
        }
        insert_rows([row])
        s3.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": key},
            Key=key.replace("incoming/", "processed/", 1),
        )
        s3.delete_object(Bucket=bucket, Key=key)
        inserted += 1
    return {"inserted": inserted}
