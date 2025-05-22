"""
Database Module for Process Project Files Lambda
-------------------------------------------------------------
This file contains functions for interacting with MongoDB for the process_project_files_lambda.
"""

import os
import datetime
from loguru import logger
from pymongo import MongoClient

# Config
MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "CPMAI")


class DatabaseManager:
    """Class for managing database operations"""

    def __init__(self):
        """Initialize the database manager"""
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[MONGODB_DB_NAME]

    def get_files_info(self, project_id):
        """
        Get file info from the database

        Args:
            project_id (str): The ID of the project

        Returns:
            dict: The file info document, or None if not found
        """
        try:
            return self.db["uploaded_files"].find({"project_id": project_id})
        except Exception as e:
            logger.error(f"Error retrieving file info: {e}")
            return None

    def update_project_status(self, project_id, status="completed"):
        """
        Update project status in the database

        Args:
            project_id (str): The ID of the project
            status (str): The new status

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.db["projects"].update_one(
                {"project_id": project_id},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                    }
                },
            )

            if result.modified_count > 0:
                logger.info(
                    f"Successfully updated project status to {status} for project {project_id}"
                )
                return True
            else:
                logger.warning(
                    f"No project documents were updated in MongoDB for project {project_id}"
                )
                return False
        except Exception as e:
            logger.error(f"Error updating project status: {e}")
            return False

    def update_file(self, file):
        """
        Update file in the database

        Args:
            file (FileInfo): The file object to update

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_dict = file.dict()
            result = self.db["uploaded_files"].update_one(
                {"_id": file._id},
                {"$set": file_dict},
            )

            if result.modified_count > 0:
                logger.info(
                    f"Successfully updated file {file.file_name} in MongoDB"
                )
                return True
            else:
                logger.warning(
                    f"No file documents were updated in MongoDB for file {file.file_name}"
                )
                return False
        except Exception as e:
            logger.error(f"Error updating file: {e}")
            return False
