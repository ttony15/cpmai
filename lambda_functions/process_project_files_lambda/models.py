"""
Project Files Processing Lambda Models
-------------------------------------------------------------
This file contains the model definitions used by the process_project_files_lambda.
"""

import datetime


class Project:
    """Model for storing project information in MongoDB"""

    collection_name = "projects"

    def __init__(
        self,
        project_id,
        user_id,
        name,
        description=None,
        status="created",
        created_at=None,
        updated_at=None,
        **kwargs,
    ):
        self.project_id = project_id
        self.user_id = user_id
        self.name = name
        self.description = description
        self.status = status
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc)
        self.updated_at = updated_at
        self._id = kwargs.get("_id")

    def dict(self):
        """Convert the project to a dictionary"""
        return {
            "project_id": self.project_id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data):
        """Create a Project instance from a dictionary"""
        return cls(**data)


class FileInfo:
    """Model for storing uploaded file information"""

    def __init__(
        self,
        _id,
        file_name,
        s3_key,
        embeddings,
        created_at,
        project_id,
        user_id,
        file_description="",
        document_category="other",
        analysis_result=None,
    ):
        self._id = _id
        self.file_name = file_name
        self.s3_key = s3_key
        self.file_description = file_description
        self.document_category = document_category
        self.analysis_result = analysis_result
        self.embeddings = embeddings
        self.created_at = created_at
        self.project_id = project_id
        self.user_id = user_id

    def dict(self):
        """Convert the uploaded file to a dictionary"""
        return {
            "_id": self._id,
            "embeddings": self.embeddings,
            "file_name": self.file_name,
            "s3_key": self.s3_key,
            "file_description": self.file_description,
            "document_category": self.document_category,
            "analysis_result": self.analysis_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "project_id": self.project_id,
            "user_id": self.user_id,
        }

    @classmethod
    def from_dict(cls, data):
        """Create an UploadedFile instance from a dictionary"""
        return cls(**data)
