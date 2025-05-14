import datetime
import zoneinfo

from beanie import Document
from pydantic import Field


class TrainFiles(Document):
    file_hash: str
    file_key: str


class TrainedModel(Document):
    id: str
    model_name: str | None = None
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(tz=zoneinfo.ZoneInfo("UTC"))
    )
