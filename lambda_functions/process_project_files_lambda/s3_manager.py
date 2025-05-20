"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Please use the file_service.py module instead.
"""

import os
import boto3
from loguru import logger
from botocore.exceptions import ClientError
from lambda_functions.process_project_files_lambda.file_service import S3Manager

# Create a warning about deprecation
logger.warning("The s3_manager module is deprecated. Please use the file_service module instead.")

# Config
S3_BUCKET = os.environ.get("S3_BUCKET")
ACCESS_KEY = os.environ.get("S3_ACCESS_KEY")
SECRET_KEY = os.environ.get("S3_SECRET_KEY")


def download_file(s3_key):
    """
    DEPRECATED: Download a file from S3 using the provided S3 key

    This function is deprecated and will be removed in a future version.
    Please use S3Manager.download_file() instead.

    Args:
        s3_key (str): The S3 key (path) of the file to download

    Returns:
        bytes or str: The content of the file as bytes (for binary files like PDFs) or
                     as a string (for text files), or None if an error occurs
    """
    logger.warning("The download_file function is deprecated. Please use S3Manager.download_file() instead.")

    # Use the new service to maintain backward compatibility
    s3_manager = S3Manager()
    return s3_manager.download_file(s3_key)
