"""
Project Files Processing Lambda
-------------------------------------------------------------
This Lambda function processes files associated with a project based on event data.

Workflow:
1. Receives event data containing:
   - project_id: The ID of the project to process
   - user_id: The ID of the user who owns the project
   - action: The action to perform (must be "process")

2. Queries MongoDB to find files associated with the project_id and user_id

3. Processes each file based on its category (e.g., drawing, specification, quote, etc.)

The Lambda function returns a success response if all files are processed successfully,
or an error response if any issues occur during processing.
"""

import json
import os

from loguru import logger

from business_logic import process_files
from models import FileInfo
from pymongo import MongoClient

# Config
MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "CPMAI")


# Initialize MongoDB connection
def init_db():
    """Initialize the database connection"""
    client = MongoClient(MONGODB_URI)
    return client[MONGODB_DB_NAME]


# Function to get project details
def get_project_details(project_id):
    """Get project details from the database"""
    try:
        # Initialize the database connection
        db = init_db()

        # Find the project by project_id
        project_data = db[FileInfo.collection_name].find_one({"project_id": project_id})

        if project_data:
            # Convert MongoDB document to Project object
            project = FileInfo.from_dict(project_data)
            logger.info(f"Retrieved project details for project ID: {project_id}")
            return project
        else:
            logger.warning(f"Project with ID {project_id} not found")
            return None
    except Exception as e:
        logger.error(f"Error retrieving project details: {e}")
        return None


# Main Lambda handler
def lambda_handler(event, context):
    """
    Lambda function handler that processes event data, retrieves project files,
    and processes those files.

    Args:
        event: The event data containing project_id, user_id, and action
        context: The context object from AWS Lambda

    Returns:
        A dictionary containing the processing status or an error message
    """
    try:
        # Extract data from the event
        message = event

        if not message:
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No data to process"}),
            }

        # Extract project_id and user_id from the event
        project_id = message.get("project_id")
        user_id = message.get("user_id")
        action = message.get("action")

        if not project_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing project_id in the message"}),
            }

        if not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing user_id in the message"}),
            }

        if action != "process":
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Unsupported action: {action}"}),
            }

        # Get project details to verify the project exists
        project_details = get_project_details(project_id)

        if not project_details:
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {"error": f"Project with ID {project_id} not found"}
                ),
            }

        # Process the files
        processing_result = process_files(project_details)

        if processing_result:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "status": "success",
                        "message": f"Successfully processed {len(project_details.files)} files for project {project_id}",
                        "project_id": project_id,
                        "user_id": user_id,
                        "file_count": len(project_details.files),
                    }
                ),
            }
        else:
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "status": "error",
                        "message": f"Failed to process files for project {project_id}",
                        "project_id": project_id,
                        "user_id": user_id,
                    }
                ),
            }

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal server error: {str(e)}"}),
        }
