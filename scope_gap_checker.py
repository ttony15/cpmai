"""scope_gap_checker.py – Missing-Scope Checker API (v1)
====================================================

## Purpose
This FastAPI service identifies scope gaps by comparing:
  - **Expected scope** (drawing-derived) from `trade_scopes`
  - **Quoted scope** (bidder-provided) from `quotes`
Any missing scope items are returned and automatically queued for human review.

## Key Features
- `POST /missing-scope` endpoint (JWT-secured)
- Fetch data from Aurora Postgres (`trade_scopes`, `quotes`)
- Compute missing items per trade
- Push each gap to an SQS review queue (`SCOPE_REVIEW_QUEUE_URL`)
- Rich `##` code comments for developer clarity

"""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Dict, List

import boto3
import requests
import psycopg2
from fastapi import Depends, FastAPI, HTTPException, Request
from jose import jwk, jwt as jose_jwt
from psycopg2.extras import RealDictCursor
from starlette.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
## CONFIGURATION
# ---------------------------------------------------------------------------
DB_SECRET_ID             = os.environ["DB_SECRET_ID"]
JWKS_URL                 = os.environ["JWKS_URL"]
SCOPE_REVIEW_QUEUE_URL   = os.environ.get("SCOPE_REVIEW_QUEUE_URL")  # SQS for scope-review

# Thresholds and constants
# (none for now -- we queue every missing item)

# ---------------------------------------------------------------------------
## LOGGER
# ---------------------------------------------------------------------------
logger = logging.getLogger("scope_gap_checker")
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
## AWS CLIENTS
# ---------------------------------------------------------------------------
ssm = boto3.client("secretsmanager")
sqs = boto3.client("sqs")

# ---------------------------------------------------------------------------
## DATABASE CONNECTION
# ---------------------------------------------------------------------------
# Fetch DB credentials from Secrets Manager
db_creds = json.loads(ssm.get_secret_value(SecretId=DB_SECRET_ID)["SecretString"])
conn = psycopg2.connect(
    host=db_creds["host"], port=db_creds["port"], user=db_creds["username"],
    password=db_creds["password"], dbname=db_creds["dbname"], sslmode="require",
    cursor_factory=RealDictCursor
)
conn.autocommit = True

# ---------------------------------------------------------------------------
## JWT AUTH SETUP
# ---------------------------------------------------------------------------
# Load JWKS for JWT verification
jwks = requests.get(JWKS_URL, timeout=3).json()
key_set = {k['kid']: k for k in jwks['keys']}


def verify_jwt(token: str = Depends(lambda req: req.headers.get("Authorization","").split()[-1])) -> Dict[str,Any]:
    """
    Ensure each request has a valid JWT bearer token.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    header = jose_jwt.get_unverified_header(token)
    key_data = key_set.get(header['kid'])
    if not key_data:
        raise HTTPException(status_code=401, detail="Invalid token key ID")
    key = jwk.construct(key_data)
    payload = jose_jwt.decode(token, key.to_dict(), algorithms=[header['alg']])
    return payload  # returns claims, including `sub`

# ---------------------------------------------------------------------------
## FASTAPI APP
# ---------------------------------------------------------------------------
app = FastAPI(title="Scope Gap Checker", version="0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

# ---------------------------------------------------------------------------
## HELPER: FETCH SCOPE & QUOTE DATA
# ---------------------------------------------------------------------------
def fetch_scopes_and_quotes(project_id: str) -> Dict[str, Any]:
    """
    Retrieve:
      - trade_scopes.scope_items (expected)
      - quotes.scope (quoted)
    Group by trade for comparison.
    """
    result: Dict[str, Any] = {'expected': {}, 'quoted': {}}
    with conn.cursor() as cur:
        # 1) Expected scope from drawings
        cur.execute(
            "SELECT trade, scope_json->'scope_items' AS items "
            "FROM trade_scopes WHERE project_id=%s", (project_id,)
        )
        for row in cur.fetchall():
            trade = row['trade']
            items = [i.get('item') for i in row['items']]
            result['expected'][trade] = set(items)

        # 2) Quoted scope from vendor bids
        cur.execute(
            "SELECT trade, scope "
            "FROM quotes WHERE project_id=%s", (project_id,)
        )
        for row in cur.fetchall():
            trade = row['trade']
            # scope is stored as JSON array of strings
            items = row.get('scope') or []
            # accumulate per trade across multiple quotes
            result['quoted'].setdefault(trade, set()).update(items)
    return result

# ---------------------------------------------------------------------------
## HELPERS: IDENTIFY MISSING ITEMS & QUEUE FOR REVIEW
# ---------------------------------------------------------------------------
def identify_and_queue_gaps(
    project_id: str, user_id: str, data: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    For each trade:
      - compute expected minus quoted
      - if any gaps, send to SQS review queue
    Return dict of missing items per trade.
    """
    missing_map: Dict[str, List[str]] = {}
    for trade, expected in data['expected'].items():
        quoted = data['quoted'].get(trade, set())
        gaps = list(expected - quoted)
        if gaps:
            missing_map[trade] = gaps
            # auto-queue for human review
            if SCOPE_REVIEW_QUEUE_URL:
                payload = {
                    'project_id': project_id,
                    'user_id': user_id,
                    'trade': trade,
                    'missing_items': gaps,
                    'timestamp': __import__('time').time()
                }
                sqs.send_message(
                    QueueUrl=SCOPE_REVIEW_QUEUE_URL,
                    MessageBody=json.dumps(payload)
                )
                logger.info(f"Queued missing scope for review: {trade}, items={gaps}")
    return missing_map

# ---------------------------------------------------------------------------
## ENDPOINT: POST /missing-scope
# ---------------------------------------------------------------------------
@app.post("/missing-scope")
async def missing_scope(
    request: Request,
    auth: Dict[str, Any] = Depends(verify_jwt)
):
    """
    Identify and return missing scope items per trade.
    Authenticated via JWT.
    """
    body = await request.json()
    project_id = body.get('project_id')
    user_id = auth.get('sub')

    if not project_id:
        raise HTTPException(status_code=400, detail="Missing project_id in request")

    # Fetch data
    data = fetch_scopes_and_quotes(project_id)
    # Identify gaps & queue for review
    missing = identify_and_queue_gaps(project_id, user_id, data)

    return {
        'project_id': project_id,
        'missing_scopes': missing
    }


