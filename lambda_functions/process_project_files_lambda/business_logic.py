"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Please use the service.py module instead.
"""

from loguru import logger
from lambda_functions.process_project_files_lambda.service import ProjectFileService

# Create a warning about deprecation
logger.warning("The business_logic module is deprecated. Please use the service module instead.")

# Function to process project files (deprecated)
def process_files(file_info):
    """
    DEPRECATED: Process files associated with a project

    This function is deprecated and will be removed in a future version.
    Please use ProjectFileService.process_files() instead.
    """
    logger.warning("The process_files function is deprecated. Please use ProjectFileService.process_files() instead.")

    # Use the new service to maintain backward compatibility
    service = ProjectFileService()
    return service.process_files(file_info)
