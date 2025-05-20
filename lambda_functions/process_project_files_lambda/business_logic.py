from loguru import logger
from lambda_functions.process_project_files_lambda.s3_manager import download_file
from lambda_functions.process_project_files_lambda.gemini_manager import send_to_gemini
import os
import datetime
from pymongo import MongoClient

# Config
MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "CPMAI")

# Initialize MongoDB connection
def init_db():
    """Initialize the database connection"""
    client = MongoClient(MONGODB_URI)
    return client[MONGODB_DB_NAME]


# Function to process project files
def process_files(file_info):
    """Process files associated with a project"""
    try:
        if not file_info or not file_info.files:
            logger.warning("No files to process")
            return False

        logger.info(f"Processing {len(file_info.files)} files")

        # Process each file
        for file in file_info.files:
            logger.info(
                f"Processing file: {file.file_name}, Category: {file.document_category}"
            )

            # 1. Download the file from S3
            file_content = download_file(file.s3_key)
            if not file_content:
                logger.error(f"Failed to download file: {file.file_name}")
                continue

            # 2. Send the file content to Gemini for processing
            analysis_result = send_to_gemini(
                file_content, file.file_name, file.document_category
            )

            if analysis_result:
                # 3. Update the file object with the analysis result
                file.analysis_result = analysis_result
                logger.info(f"Successfully processed file: {file.file_name}")
            else:
                logger.error(f"Failed to process file with Gemini: {file.file_name}")

        # 4. Save the updated file_info back to MongoDB
        try:
            db = init_db()
            collection = db["file_info"]

            # Update the MongoDB record with the modified file_info
            result = collection.update_one(
                {"project_id": file_info.project_id},
                {"$set": {"files": [file.dict() for file in file_info.files]}}
            )

            if result.modified_count > 0:
                logger.info(f"Successfully updated file_info in MongoDB for project {file_info.project_id}")
            else:
                logger.warning(f"No documents were updated in MongoDB for project {file_info.project_id}")

            # Update project status to completed
            projects_collection = db["projects"]
            project_result = projects_collection.update_one(
                {"project_id": file_info.project_id},
                {"$set": {"status": "completed", "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
            )

            if project_result.modified_count > 0:
                logger.info(f"Successfully updated project status to completed for project {file_info.project_id}")
            else:
                logger.warning(f"No project documents were updated in MongoDB for project {file_info.project_id}")

            logger.info("File processing completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating MongoDB: {e}")
            return False
    except Exception as e:
        logger.error(f"Error processing files: {e}")
        return False
