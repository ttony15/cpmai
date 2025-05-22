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

from loguru import logger
from lambda_functions.process_project_files_lambda.controller import LambdaController

# Initialize the controller
controller = LambdaController()


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
    logger.info("Processing Lambda event")
    return controller.handle_event(event)
