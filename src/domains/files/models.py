from beanie import Document
from pydantic import Field, BaseModel
from typing import List, Optional
import datetime
import zoneinfo


class UploadedFile(BaseModel):
    file_name: str
    s3_key: str
    file_description: str = ""
    document_category: str = "other"  # drawing, specification, quote, contract, schedule, other


class FileInfo(Document):
    """Model for storing file information in MongoDB"""

    user_id: str
    project_id: str
    files: List[UploadedFile] = Field(default_factory=list)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(tz=zoneinfo.ZoneInfo("UTC"))
    )
    updated_at: Optional[datetime.datetime] = None

    class Settings:
        name = "file_info"
