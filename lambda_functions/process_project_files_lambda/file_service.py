"""
File Service Module for Process Project Files Lambda
-------------------------------------------------------------
This file contains classes for interacting with AWS S3 for the process_project_files_lambda.
"""

import os
import boto3
from loguru import logger
from botocore.exceptions import ClientError

# Config
S3_BUCKET = os.environ.get("S3_BUCKET")
ACCESS_KEY = os.environ.get("S3_ACCESS_KEY")
SECRET_KEY = os.environ.get("S3_SECRET_KEY")


class S3Manager:
    """Class for managing S3 operations"""

    def __init__(self):
        """Initialize the S3 manager"""
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
        )
        self.bucket = S3_BUCKET

    def download_file(self, s3_key):
        """
        Download a file from S3 using the provided S3 key

        Args:
            s3_key (str): The S3 key (path) of the file to download

        Returns:
            bytes or str: The content of the file as bytes (for binary files like PDFs) or
                         as a string (for text files), or None if an error occurs
        """
        try:
            logger.info(f"Downloading file from S3: {s3_key}")
            
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)

            # Read the file content as bytes
            file_content = response["Body"].read()
            logger.info(f"Successfully downloaded file: {s3_key}")

            return file_content
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading file from S3: {e}")
            return None