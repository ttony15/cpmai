from beanie import Document
from pydantic import Field
import datetime
import zoneinfo
from typing import Optional


class Project(Document):
    """Model for storing project information in MongoDB"""

    project_id: str
    user_id: str
    name: str
    description: Optional[str] = None
    status: str = "created"  # created, in_progress, completed, failed
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(tz=zoneinfo.ZoneInfo("UTC"))
    )
    updated_at: Optional[datetime.datetime] = None

    class Settings:
        name = "projects"
