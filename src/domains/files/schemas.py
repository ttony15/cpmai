import hashlib
from typing import List, Literal

from fastapi import UploadFile
from pydantic import BaseModel, model_validator


class FileDetails(BaseModel):
    file: UploadFile
    contents: bytes | None = None
    file_hash: str | None = None

    @model_validator(mode="before")
    def encode_file(cls, values):
        file_content = values.get("file").file.read()

        # Calculate SHA-256 hash
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        values["file_hash"] = sha256_hash

        # Base64 encode the content
        values["contents"] = file_content

        # Reset file pointer to beginning for potential future reads
        values.get("file").file.seek(0)

        return values


class FileInput(BaseModel):
    user_id: str
    project_id: str | None = None
    file_details: List[FileDetails] | None = None


class GetFilesInput(BaseModel):
    """Input schema for retrieving files for a user and project"""

    user_id: str
    project_id: str


class FileInfo(BaseModel):
    """Schema for file information returned by get_files"""

    file_name: str
    s3_key: str
    file_description: str = ""
    document_category: str = "other"  # drawing, specification, quote, contract, schedule, other


class GetFilesOutput(BaseModel):
    """Output schema for get_files response"""

    status: Literal["success", "error"]
    message: str
    files: List[FileInfo] = []


class UploadedFileInfo(BaseModel):
    """Schema for uploaded file information returned by upload_file"""

    file_name: str
    s3_url: str


class UploadFileOutput(BaseModel):
    """Output schema for upload_file response"""

    status: Literal["success", "error"]
    message: str
    files: List[UploadedFileInfo] = []


class UpdateFileDescriptionInput(BaseModel):
    """Input schema for updating file description"""

    s3_key: str
    file_description: str
    document_category: Literal["drawing", "specification", "quote", "contract", "schedule", "other"] = "other"


class UpdateFileDescriptionOutput(BaseModel):
    """Output schema for update_file_description response"""

    status: Literal["success", "error"]
    message: str
    file: FileInfo | None = None
