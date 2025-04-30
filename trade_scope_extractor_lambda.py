### services/trade_scope_extractor_lambda.py
"""
W2B – Trade Scope Extractor (enhanced v2)
-------------------------------------------------------------
This Lambda reads classified sheet entries, groups by trade, retrieves OCR/snippets,
invokes a Model Router to generate detailed scope JSON, computes risk score,
and writes to `trade_scopes` or queues review.
"""
import os
import json
import logging
import boto3
import asyncio
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
import openai
import anthropic
from math import sqrt

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)

# Config
DB_SECRET_ID      = os.environ["DB_SECRET_ID"]
OPENAI_SECRET     = os.environ["OPENAI_SECRET"]
ANTHROPIC_SECRET  = os.environ["ANTHROPIC_SECRET"]
TABLE_SCOPE       = os.environ.get("TABLE_SCOPE", "trade_scopes")
TABLE_REVIEW      = os.environ.get("TABLE_REVIEW", "scope_review_queue")
BUCKET            = os.environ.get("DRAWING_BUCKET", "cpm-drawings")
CAPTION_ENDPOINT  = os.environ.get("CAPTION_MODEL_ENDPOINT")
CONTEXT_K         = int(os.environ.get("RAG_TOP_K", 5))
CONF_THRESH       = float(os.environ.get("CONFIDENCE_THRESHOLD", 0.2))

# Clients
ssm = boto3.client("secretsmanager")
s3  = boto3.client("s3")
# secrets
openai.api_key = json.loads(ssm.get_secret_value(SecretId=OPENAI_SECRET)["SecretString"])["OPENAI_API_KEY"]
ant_key = json.loads(ssm.get_secret_value(SecretId=ANTHROPIC_SECRET)["SecretString"])["ANTHROPIC_API_KEY"]
ant_client = anthropic.Client(api_key=ant_key)
# db
db_cfg = json.loads(ssm.get_secret_value(SecretId=DB_SECRET_ID)["SecretString"])
conn = psycopg2.connect(**db_cfg, sslmode="require")
conn.autocommit = True
# embedding model
EMB_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# Utils: cosine sim

def cosine(a,b):
    dot = sum(x*y for x,y in zip(a,b))
    na = sqrt(sum(x*x for x in a))
    nb = sqrt(sum(y*y for y in b))
    return dot/(na*nb) if na and nb else 0

async def call_llm(model, prompt):
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[{"role":"system","content":"Return JSONONLY."},{"role":"user","content":prompt}],
        temperature=0,
        response_format={"type":"json_object"}
    )
    return resp.choices[0].message.content

async def verify_scope(scope_json):
    prompt = f"Rate risk between 0-1 for this scope: {json.dumps(scope_json)}"
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0,
        response_format={"type":"json_object"}
    )
    return float(json.loads(resp.choices[0].message.content)["risk_score"])

# Main
 def lambda_handler(event, context):
    project_id = event["project_id"]
    # fetch classified sheets
    with conn.cursor() as cur:
        cur.execute("SELECT sheet_id,trade FROM sheet_class WHERE project_id=%s",(project_id,))
        meta = cur.fetchall()
    by_trade = {}
    for sheet_id,trade in meta:
        key = f"full/{project_id}/{sheet_id}.pdf"
        # get text + caption
        txt = pdfplumber.open(io.BytesIO(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read())).pages[0].extract_text() or ""
        cap = await caption_image(key)
        emb = EMB_MODEL.encode(cap+txt)
        by_trade.setdefault(trade,[]).append((sheet_id,cap+txt,emb))
    output=[]
    with conn.cursor() as cur:
        for trade,entries in by_trade.items():
            # RAG: pick top K by cosine
            q_emb = EMB_MODEL.encode(event.get("question",""))
            ranked = sorted(entries, key=lambda e: cosine(q_emb,e[2]), reverse=True)[:CONTEXT_K]
            prompt = f"Trade {trade}, context: {[e[1] for e in ranked]}"
            # choose model
            model = "gpt-4o-128k"
            scope_json = asyncio.run(call_llm(model,prompt))
            risk = asyncio.run(verify_scope(scope_json))
            # queue review or insert
            if risk>CONF_THRESH:
                cur.execute(f"INSERT INTO {TABLE_REVIEW}(project_id,trade,scope_json,risk_score) VALUES(%s,%s,%s,%s)",(project_id,trade,json.dumps(scope_json),risk))
            else:
                cur.execute(f"INSERT INTO {TABLE_SCOPE}(project_id,trade,scope_json) VALUES(%s,%s,%s) ON CONFLICT(project_id,trade) DO UPDATE SET scope_json=EXCLUDED.scope_json",(project_id,trade,json.dumps(scope_json)))
    return {"status":"ok"}
