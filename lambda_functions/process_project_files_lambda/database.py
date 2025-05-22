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

    def get_file_info(self, project_id):
        """
        Get file info from the database
        
        Args:
            project_id (str): The ID of the project
            
        Returns:
            dict: The file info document, or None if not found
        """
        try:
            return self.db["file_info"].find_one({"project_id": project_id})
        except Exception as e:
            logger.error(f"Error retrieving file info: {e}")
            return None

    def update_file_info(self, project_id, files):
        """
        Update file info in the database
        
        Args:
            project_id (str): The ID of the project
            files (list): The list of file objects
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.db["file_info"].update_one(
                {"project_id": project_id},
                {"$set": {"files": files}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Successfully updated file_info in MongoDB for project {project_id}")
                return True
            else:
                logger.warning(f"No documents were updated in MongoDB for project {project_id}")
                return False
        except Exception as e:
            logger.error(f"Error updating file info: {e}")
            return False

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
                {"$set": {"status": status, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Successfully updated project status to {status} for project {project_id}")
                return True
            else:
                logger.warning(f"No project documents were updated in MongoDB for project {project_id}")
                return False
        except Exception as e:
            logger.error(f"Error updating project status: {e}")
            return False