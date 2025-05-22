from pydantic import BaseModel, Field
from typing import List, Optional
import datetime


class ProjectBase(BaseModel):
    """Base schema for Project"""
    project_id: str
    user_id: str
    status: str
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None


class ProjectCreate(BaseModel):
    """Schema for creating a new project"""
    name: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(ProjectBase):
    """Schema for project response"""
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectListResponse(BaseModel):
    """Schema for project list response"""
    total: int
    page: int
    page_size: int
    projects: List[ProjectResponse]
