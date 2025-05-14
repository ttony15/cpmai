import hashlib
import uuid
from datetime import datetime

from fastapi import UploadFile
from loguru import logger


from src.domains.chat.schemas import UploadResult, ChatInput, ChatResult
from src.integrations.awsS3.manager import upload as s3_upload
from src.integrations.awsSQS.manager import send_message as sqs_send


async def upload_file(
    file: UploadFile, file_type: str, project_id: str
) -> UploadResult:
    """Upload a file to S3 and trigger queue for processing"""

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    file_id = str(uuid.uuid4())

    s3_key = f"raw/{file_id}/{file.filename}"
    content_type = (
        "application/pdf"
        if file.filename.endswith(".pdf")
        else "application/octet-stream"
    )

    s3_url = await s3_upload(
        file_name=s3_key, file_content=content, content_type=content_type
    )

    if not s3_url:
        logger.error(f"Failed to upload file: {file.filename}")
        # You might want to handle this error case appropriately
    else:
        # If S3 upload succeeded
        message = {
            "file_id": file_id,
            "s3_key": s3_key,
            "hash": file_hash,
            "file_type": file_type,
            "project_id": project_id,
            "filename": file.filename,
            "timestamp": datetime.utcnow().isoformat(),
        }
        sqs_response = await sqs_send(message)
        if sqs_response:
            logger.info(f"File sent to processing queue: {file_id}")
        else:
            logger.warning(f"Failed to send message to SQS for file: {file_id}")

    return UploadResult(
        file_id=file_id, s3_key=s3_key, file_hash=file_hash, filename=file.filename
    )


async def process_chat(prompt_input: ChatInput) -> ChatResult:
    """Main flow for processing a chat with optional documents"""


async def get_project_chats(project_id: str):
    """Get all chats for a project"""
    # Todo:
    # Implement logic
    return {"project_id": project_id, "chats": []}
