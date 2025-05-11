import hashlib
import uuid
import json
from typing import Optional

from fastapi import UploadFile
from datetime import datetime


from domains.prompt.schemas import UploadResult, PromptInput, PromptResult
from loguru import logger

from old.ingestion_service import SQS_QUEUE_URL

s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")


async def upload_file(
    file: UploadFile, file_type: str, project_id: Optional[str] = None
) -> UploadResult:
    """Upload a file to S3 and trigger queue for processing"""

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    file_id = str(uuid.uuid4())

    s3_key = f"raw/{file_id}/{file.filename}"
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=content,
        ContentType="application/pdf"
        if file.filename.endswith(".pdf")
        else "application/octet-stream",
    )
    if SQS_QUEUE_URL:
        message = {
            "file_id": file_id,
            "s3_key": s3_key,
            "hash": file_hash,
            "file_type": file_type,
            "project_id": project_id or "",
            "filename": file.filename,
            "timestamp": datetime.utcnow().isoformat(),
        }
        sqs_client.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(message))
        logger.info(f"File sent to processing queue: {file_id}")

    return UploadResult(
        file_id=file_id, s3_key=s3_key, file_hash=file_hash, filename=file.filename
    )


async def process_prompt(prompt_input: PromptInput) -> PromptResult:
    """Main flow for processing a prompt with optional documents"""
