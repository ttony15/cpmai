from beanie import Document
from pydantic import Field
from typing import List, Optional
import datetime
import zoneinfo


class UploadedFile(Document):
    file_name: str
    s3_key: str
    user_id: str
    project_id: str
    file_description: str = ""
    document_category: str = (
        "other"  # drawing, specification, quote, contract, schedule, other
    )
    analysis_result: Optional[dict] = None
    embeddings: List[float] | None = None
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(tz=zoneinfo.ZoneInfo("UTC"))
    )

    class Settings:
        name = "uploaded_files"


