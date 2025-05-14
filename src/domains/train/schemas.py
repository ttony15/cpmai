import hashlib
from enum import Enum

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


class TrainIn(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    file: UploadFile
    file_type: TrainFileOptions
    domain: TrainFileDomain
    file_details: FileDetails | None = None

    @field_validator("file", mode="before")
    def validate_file_type(cls, file: UploadFile) -> UploadFile:
        if file is not None:
            allowed_extensions = settings.allowed_file_extensions
            if not any(
                file.filename.lower().endswith(ext) for ext in allowed_extensions
            ):
                raise train_exceptions.InvalidFileType().as_exception()
        return file


class TrainOut(BaseModel):
    message: str
    progress_url: str | None = None
