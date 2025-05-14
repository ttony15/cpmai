import base64
import hashlib
from enum import Enum
from typing import List

from fastapi import UploadFile
from pydantic import BaseModel, field_validator, model_validator

from src.core.settings import settings
import src.domains.train.exceptions as train_exceptions


class TrainFileOptions(str, Enum):
    textbooks = "textbooks"
    drawings = "drawings"


class TrainFileDomain(str, Enum):
    general = "general"
    structural = "structural"
    mechanical = "mechanical"
    electrical = "electrical"
    aerospace = "aerospace"
    civil = "civil"
    engineering = "engineering"
    finance = "finance"
    geological = "geological"


class FileDetails(BaseModel):
    file: UploadFile
    contents: str | None = None
    file_hash: str | None = None

    @model_validator(mode="before")
    def encode_file(cls, values):
        file_content = values.get("file").file.read()

        # Calculate SHA-256 hash
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        values["file_hash"] = sha256_hash

        # Base64 encode the content
        values["contents"] = base64.b64encode(file_content).decode("utf-8")

        # Reset file pointer to beginning for potential future reads
        values.get("file").file.seek(0)

        return values


class TrainIn(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    files: List[UploadFile]
    file_type: TrainFileOptions
    domain: TrainFileDomain
    files_details: List[FileDetails] | None = None

    @field_validator("files", mode="before")
    def validate_file_type(cls, files: List[UploadFile]) -> List[UploadFile]:
        for file in files:
            if file is not None:
                allowed_extensions = settings.allowed_file_extensions
                if not any(
                    file.filename.lower().endswith(ext) for ext in allowed_extensions
                ):
                    raise train_exceptions.InvalidFileType().as_exception()

        return files


class TrainOut(BaseModel):
    message: str
    progress_url: str
