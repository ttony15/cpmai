"""
Controller Module for Process Project Files Lambda
-------------------------------------------------------------
This file contains the controller for handling Lambda events for the process_project_files_lambda.
"""

import json
from loguru import logger
from lambda_functions.process_project_files_lambda.database import DatabaseManager
from lambda_functions.process_project_files_lambda.service import ProjectFileService
from lambda_functions.process_project_files_lambda.models import FileInfo


class LambdaController:
    """Controller for handling Lambda events"""

    def __init__(self, ai_service_type="gemini"):
        """
        Initialize the Lambda controller
        
        Args:
            ai_service_type (str): The type of AI service to use (gemini or openai)
        """
        self.db_manager = DatabaseManager()
        self.file_service = ProjectFileService(ai_service_type)

    def handle_event(self, event):
        """
        Handle a Lambda event
        
        Args:
            event: The Lambda event
            
        Returns:
            dict: The response to return from the Lambda function
        """
        try:
            # Extract data from the event
            message = event

            if not message:
                return self._create_response(200, {"message": "No data to process"})

            # Extract project_id and user_id from the event
            project_id = message.get("project_id")
            user_id = message.get("user_id")
            action = message.get("action")

            # Validate the event data
            if not project_id:
                return self._create_response(400, {"error": "Missing project_id in the message"})

            if not user_id:
                return self._create_response(400, {"error": "Missing user_id in the message"})

            if action != "process":
                return self._create_response(400, {"error": f"Unsupported action: {action}"})

            # Get project details to verify the project exists
            project_data = self.db_manager.get_file_info(project_id)

            if not project_data:
                return self._create_response(404, {"error": f"Project with ID {project_id} not found"})

            # Convert MongoDB document to FileInfo object
            file_info = FileInfo.from_dict(project_data)

            # Process the files
            processing_result = self.file_service.process_files(file_info)

            if processing_result:
                return self._create_response(
                    200,
                    {
                        "status": "success",
                        "message": f"Successfully processed {len(file_info.files)} files for project {project_id}",
                        "project_id": project_id,
                        "user_id": user_id,
                        "file_count": len(file_info.files),
                    }
                )
            else:
                return self._create_response(
                    500,
                    {
                        "status": "error",
                        "message": f"Failed to process files for project {project_id}",
                        "project_id": project_id,
                        "user_id": user_id,
                    }
                )

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return self._create_response(500, {"error": f"Internal server error: {str(e)}"})

    def _create_response(self, status_code, body):
        """
        Create a response object
        
        Args:
            status_code (int): The HTTP status code
            body (dict): The response body
            
        Returns:
            dict: The response object
        """
        return {
            "statusCode": status_code,
            "body": json.dumps(body),
        }