"""
MVP Ingestion Service for CPM-AI
--------------------------------
FastAPI service that:
1. Accepts PDF uploads from React UI
2. Computes SHA-256 hashes for deduplication
3. Stores files to S3
4. Emits SQS messages for processing
"""

import io
import json
import logging
import os
import hashlib
import uuid
from typing import Optional
from datetime import datetime

import boto3
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configuration
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

S3_BUCKET = os.environ.get("S3_BUCKET", "cpm-raw-docs")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")

# AWS clients
s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# FastAPI app
app = FastAPI(title="CPM-AI Ingestion Service", version="0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])


class UploadResponse(BaseModel):
    file_id: str
    s3_key: str
    hash: str
    message: str


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content"""
    return hashlib.sha256(content).hexdigest()


def upload_to_s3(content: bytes, file_id: str, filename: str) -> str:
    """Upload file to S3 and return the key"""
    s3_key = f"raw/{file_id}/{filename}"
    s3.put_object(
        Bucket=S3_BUCKET, Key=s3_key, Body=content, ContentType="application/pdf"
    )
    return s3_key


def send_to_queue(
    file_id: str, s3_key: str, file_hash: str, file_type: str, project_id: str
):
    """Send message to SQS for processing"""
    message = {
        "file_id": file_id,
        "s3_key": s3_key,
        "hash": file_hash,
        "file_type": file_type,
        "project_id": project_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(message))


@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    file_type: str = Form(...),  # 'quote', 'drawing', or 'spec'
):
    """Upload a PDF file for processing"""

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")

    # Read file content
    content = await file.read()

    # Compute hash
    file_hash = compute_file_hash(content)

    # Generate unique file ID
    file_id = str(uuid.uuid4())

    try:
        # Upload to S3
        s3_key = upload_to_s3(content, file_id, file.filename)

        # Send to processing queue
        send_to_queue(file_id, s3_key, file_hash, file_type, project_id)

        LOG.info(f"File uploaded successfully: {file_id}")
        return UploadResponse(
            file_id=file_id,
            s3_key=s3_key,
            hash=file_hash,
            message="File uploaded successfully",
        )
    except Exception as e:
        LOG.error(f"Error processing file: {str(e)}")
        raise HTTPException(500, f"Failed to process file: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
