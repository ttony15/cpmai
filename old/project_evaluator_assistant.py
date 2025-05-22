"""project_evaluator_assistant.py – W3+RFI, RAG & Proof Enhanced (v3)
============================================================

## Purpose
This FastAPI service answers PM-style queries on a project using:
1) **RAG** over project documents (quotes & scopes)
2) **Streaming Markdown** replies via SSE
3) **Confidence scoring** with an LLM-based assessor
4) **Auto-drafted RFIs** when confidence < threshold
5) **Proof sections** citing source snippets, parsed JSON, and diff logic
6) **Audit trail** of queries and proofs for future replay

## Key Features
- `/query` endpoint with JWT auth
- Retrieval via embeddings + cosine similarity
- Streaming LLM generation (GPT-4o / Claude)
- Post-answer confidence check → push to RFI SQS queue
- Inline `##` explainers throughout code
- Writes audit records to Postgres `query_audit` table
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Tuple
from math import sqrt

import boto3
import openai
import psycopg2
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from jose import jwk, jwt as jose_jwt
from psycopg2.extras import RealDictCursor
import requests

# ---------------------------------------------------------------------------
## CONFIGURATION & CLIENTS
# ---------------------------------------------------------------------------
DB_SECRET_ID = os.environ["DB_SECRET_ID"]
OPENAI_SECRET = os.environ["OPENAI_SECRET"]
JWKS_URL = os.environ["JWKS_URL"]  # e.g. Auth0 JWKS
RFI_QUEUE_URL = os.environ.get("RFI_QUEUE_URL")  # SQS URL for auto-RFI
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.7"))
K_RETRIEVE = int(os.environ.get("RAG_TOP_K", "5"))

# AWS & service clients
ssm = boto3.client("secretsmanager")
sqs = boto3.client("sqs")

# OpenAI API key
secret = json.loads(ssm.get_secret_value(SecretId=OPENAI_SECRET)["SecretString"])
openai.api_key = secret["OPENAI_API_KEY"]

# Postgres connection (for context + audit)
db_cfg = json.loads(ssm.get_secret_value(SecretId=DB_SECRET_ID)["SecretString"])
conn = psycopg2.connect(**db_cfg, sslmode="require", cursor_factory=RealDictCursor)
conn.autocommit = True

# Load JWKS for JWT verification
jwks = requests.get(JWKS_URL, timeout=3).json()
key_set = {k["kid"]: k for k in jwks["keys"]}

# FastAPI app
app = FastAPI(title="Project Evaluator & Assistant", version="0.3")

# ---------------------------------------------------------------------------
## AUTHENTICATION DEPENDENCY
# ---------------------------------------------------------------------------


def verify_jwt(
    token: str = Depends(lambda req: req.headers.get("Authorization", "").split()[-1]),
):
    """
    Validate JWT using JWKS
    """
    if not token:
        raise HTTPException(401, "Missing bearer token")
    header = jose_jwt.get_unverified_header(token)
    key_data = key_set.get(header["kid"])
    if not key_data:
        raise HTTPException(401, "Invalid token key ID")
    key = jwk.construct(key_data)
    payload = jose_jwt.decode(token, key.to_dict(), algorithms=[header["alg"]])
    return payload  # contains `sub` as user_id


# ---------------------------------------------------------------------------
## UTILITY: COSINE SIMILARITY
# ---------------------------------------------------------------------------


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag = sqrt(sum(x * x for x in a)) * sqrt(sum(y * y for y in b))
    return dot / mag if mag else 0.0


# ---------------------------------------------------------------------------
## CONTEXT RETRIEVAL (RAG)
# ---------------------------------------------------------------------------
async def retrieve_context(question: str, ctx: Dict[str, Any]) -> str:
    """
    1) Embed question + document candidates
    2) Score and select top-K
    3) Return tagged snippets for LLM proof
    """
    candidates: List[Tuple[str, str]] = []
    # Prepare quote candidates
    for q in ctx["quotes"]:
        txt = f"QUOTE[{q['trade']}|{q['vendor']}]: price=${q['price']:.2f}, exclusions={q.get('exclusions', [])}"
        candidates.append((f"quote:{q['vendor']}", txt))
    # Prepare scope candidates
    for s in ctx["scopes"]:
        items = s["scope_json"].get("scope_items", [])
        txt = f"SCOPE[{s['trade']}]: {len(items)} items"
        candidates.append((f"scope:{s['trade']}", txt))
    texts = [question] + [t for _, t in candidates]

    # Embed all texts
    resp = openai.embeddings.create(model="text-embedding-ada-002", input=texts)
    embeddings = [r["embedding"] for r in resp["data"]]
    q_emb = embeddings[0]
    doc_embs = embeddings[1:]

    # Score similarity
    scored = []
    for (tag, txt), emb in zip(candidates, doc_embs):
        sim = cosine_similarity(q_emb, emb)
        scored.append((sim, tag, txt))
    scored.sort(reverse=True, key=lambda x: x[0])
    topk = scored[:K_RETRIEVE]

    # Build proof context
    proof_ctx = ""
    for sim, tag, txt in topk:
        proof_ctx += f"## SOURCE: {tag} (sim={sim:.2f})\n" + txt + "\n\n"
    return proof_ctx.strip()


# ---------------------------------------------------------------------------
## PROJECT CONTEXT FETCHER
# ---------------------------------------------------------------------------


def fetch_project_context(project_id: str) -> Dict[str, Any]:
    """
    Load project name, quotes, scopes, budget
    """
    ctx: Dict[str, Any] = {}
    with conn.cursor() as cur:
        # Project name
        cur.execute("SELECT name FROM projects WHERE id=%s", (project_id,))
        row = cur.fetchone()
        ctx["project_name"] = row["name"] if row else "Unknown"
        # Quotes
        cur.execute(
            "SELECT trade,vendor,price,scope,exclusions FROM quotes WHERE project_id=%s",
            (project_id,),
        )
        ctx["quotes"] = cur.fetchall() or []
        # Scopes
        cur.execute(
            "SELECT trade,scope_json FROM trade_scopes WHERE project_id=%s",
            (project_id,),
        )
        ctx["scopes"] = cur.fetchall() or []
        # Budget
        cur.execute(
            "SELECT budget_json FROM optimal_budget WHERE project_id=%s", (project_id,)
        )
        row = cur.fetchone()
        ctx["budget"] = row["budget_json"] if row else {}
    return ctx


# ---------------------------------------------------------------------------
## LLM INVOCATION
# ---------------------------------------------------------------------------
async def ask_llm_stream(model: str, system: str, prompt: str) -> str:
    """Stream chat completion tokens."""
    stream = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        stream=True,
    )
    result = ""
    async for chunk in stream:
        delta = chunk.choices[0].delta.get("content", "")
        result += delta
        yield delta
    return result


async def ask_llm_once(model: str, system: str, prompt: str) -> str:
    """Single-turn chat completion (for confidence rating)."""
    resp = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return resp.choices[0].message.content


# ---------------------------------------------------------------------------
## AUDIT TRAIL STORES
# ---------------------------------------------------------------------------
async def store_audit(
    project_id: str,
    user_id: str,
    question: str,
    proof_ctx: str,
    quotes: List[Any],
    scopes: List[Any],
    answer: str,
):
    """
    Write each query + proof to `query_audit` table for replay.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO query_audit (project_id, user_id, question,
                                     proof_context, quotes_json, scopes_json,
                                     answer, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s, NOW())
            """,
            (
                project_id,
                user_id,
                question,
                proof_ctx,
                json.dumps(quotes),
                json.dumps(scopes),
                answer,
            ),
        )


# ---------------------------------------------------------------------------
## AUTO-RFI: CONFIDENCE CHECK & QUEUE
# ---------------------------------------------------------------------------
async def check_and_queue_rfi(
    answer: str, question: str, project_id: str, user_id: str, model: str
):
    """
    Rate confidence and queue RFI if below threshold.
    """
    system = (
        "You rate the confidence of the previous answer [0-1]. "
        "Return JSON {confidence:float}."
    )
    prompt = f"Answer:\n{answer}\nRate confidence:"
    rating = 0.0
    try:
        eval_json = await ask_llm_once(model, system, prompt)
        rating = json.loads(eval_json).get("confidence", 0.0)
    except:
        rating = 0.0
    if rating < CONFIDENCE_THRESHOLD and RFI_QUEUE_URL:
        payload = {
            "project_id": project_id,
            "user_id": user_id,
            "question": question,
            "answer": answer,
            "confidence": rating,
            "timestamp": time.time(),
        }
        sqs.send_message(QueueUrl=RFI_QUEUE_URL, MessageBody=json.dumps(payload))
        logging.warning(f"Queued RFI (conf={rating:.2f}) for {project_id}")


# ---------------------------------------------------------------------------
## MODEL ROUTER
# ---------------------------------------------------------------------------
def choose_model_alias(prompt_len: int) -> str:
    """Select between GPT-4o and Claude based on prompt size."""
    return "claude-3-opus-20240229" if prompt_len > 90000 else "gpt-4o-128k"


# ---------------------------------------------------------------------------
## /query ENDPOINT
# ---------------------------------------------------------------------------
@app.post("/query")
async def query(request: Request, auth: Any = Depends(verify_jwt)):
    """
    1) Parse payload
    2) Fetch context
    3) Retrieve RAG proof_ctx
    4) Build prompts with proof instructions
    5) Stream answer
    6) Post-process: store audit + trigger RFI
    """
    data = await request.json()
    project_id = data["project_id"]
    question = data["question"]
    user_id = auth["sub"]

    # Fetch project context
    ctx = fetch_project_context(project_id)
    proof_ctx = await retrieve_context(question, ctx)

    # Build prompts (ask for explicit Proof section)
    system_prompt = (
        "You are a senior construction PM assistant. "
        "Use the provided sources. Answer in Markdown. "
        "At the end, include a '## Proof' section with:\n"
        "1) SOURCE tags (from context)\n"
        "2) Parsed quote JSON snippet\n"
        "3) Exact match/diff logic explanation\n"
    )
    user_prompt = (
        f"Project {ctx['project_name']}\nContext:\n{proof_ctx}\nQuestion: {question}\n"
    )

    # Prepare to collect answer
    answer_buf = ""
    model_alias = choose_model_alias(len(user_prompt) // 4)

    async def stream_gen():
        nonlocal answer_buf
        # Stream answer
        async for tok in ask_llm_stream(model_alias, system_prompt, user_prompt):
            answer_buf += tok
            yield tok
        # Once complete: store audit and check RFI
        await store_audit(
            project_id,
            user_id,
            question,
            proof_ctx,
            ctx["quotes"],
            ctx["scopes"],
            answer_buf,
        )
        asyncio.create_task(
            check_and_queue_rfi(answer_buf, question, project_id, user_id, model_alias)
        )

    return StreamingResponse(stream_gen(), media_type="text/markdown")
