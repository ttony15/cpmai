from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import UploadFile
import uuid


class UploadResult(BaseModel):
    file_id: str
    s3_key: str
    file_hash: str
    filename: str


class PromptInput(BaseModel):
    user_id: str
    query: str
    project_id: Optional[str] = None
    files: Optional[List[UploadFile]] = None
    file_type: str = "document"  # 'quote', 'drawing', 'spec', or 'document'

    class Config:
        arbitrary_types_allowed = True


class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_type: str
    s3_key: str
    file_hash: str


class PromptResult(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []
    file_ids: List[str] = []
    prompt_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
