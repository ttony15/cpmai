"""
Service Module for Process Project Files Lambda
-------------------------------------------------------------
This file contains the business logic service for the process_project_files_lambda.
"""

import orjson
from loguru import logger
from lambda_functions.process_project_files_lambda.database import DatabaseManager
from lambda_functions.process_project_files_lambda.file_service import S3Manager
from lambda_functions.process_project_files_lambda.ai_service import (
    AIServiceFactory,
)


class ProjectFileService:
    """Service for processing project files"""

    def __init__(self, ai_service_type="gemini"):
        """
        Initialize the project file service

        Args:
            ai_service_type (str): The type of AI service to use (gemini or openai)
        """
        self.db_manager = DatabaseManager()
        self.s3_manager = S3Manager()
        self.ai_service = AIServiceFactory.get_service(ai_service_type)

    def process_files(self, files):
        """
        Process files associated with a project

        Args:
            files: The file info object containing project and file information

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not files:
                logger.warning("No files to process")
                return False

            logger.info(f"Processing {len(files)} files")

            # Process each file
            for file in files:
                logger.info(
                    f"Processing file: {file.file_name}, Category: {file.document_category}"
                )

                if file.analysis_result:
                    continue

                # 1. Download the file from S3
                file_content = self.s3_manager.download_file(file.s3_key)
                if not file_content:
                    logger.error(f"Failed to download file: {file.file_name}")
                    continue

                # 2. Send the file content to AI service for processing
                analysis_result = self.ai_service.process_file(
                    file_content, file.file_name, file.document_category
                )

                if analysis_result:
                    # 3. Update the file object with the analysis result
                    file.analysis_result = analysis_result
                    logger.info(f"Successfully processed file: {file.file_name}")
                else:
                    logger.error(
                        f"Failed to process file with AI service: {file.file_name}"
                    )

                # Generate embeddings before saving.
                ai_service = AIServiceFactory.get_service("openai")
                file_raw_data = file.dict()
                file_raw_data.pop("_id")
                embeddings = ai_service.generate_embeddings(
                    orjson.dumps(file_raw_data).decode("utf-8")
                )
                if embeddings:
                    file.embeddings = embeddings
                    logger.info(
                        f"Successfully generated embeddings for file: {file.file_name}"
                    )
                else:
                    logger.warning(
                        f"Failed to generate embeddings for file: {file.file_name}"
                    )

            # 4. Save the updated file_info back to MongoDB
            return True
        except Exception as e:
            logger.error(f"Error processing files: {e}")
            return False
