from loguru import logger
from typing import List

from src.domains.files.schemas import (
    FileInput, GetFilesInput, GetFilesOutput, FileInfo as FileInfoSchema,
    UploadFileOutput, UploadedFileInfo, UpdateFileDescriptionInput, UpdateFileDescriptionOutput
)
from src.domains.files.models import FileInfo, UploadedFile
from src.integrations.awsS3.manager import upload as s3_upload


async def upload_file(
    file_input: FileInput, upload_type="requirements"
) -> UploadFileOutput:
    """
    Upload files to S3 and save file information in MongoDB

    Args:
        file_input: FileInput object containing user_id, project_id, and file_details
        upload_type: Type of upload (default: "requirements")

    Returns:
        UploadFileOutput object containing status, message, and files
    """
    logger.info(
        f"Uploading {len(file_input.file_details)} files for project {file_input.project_id}"
    )

    # Get or create FileInfo document
    file_info = await FileInfo.find_one(
        {"user_id": file_input.user_id, "project_id": file_input.project_id}
    )

    if not file_info:
        file_info = FileInfo(
            user_id=file_input.user_id, project_id=file_input.project_id, files=[]
        )

    uploaded_files = []

    # Upload each file to S3 and add to file_info
    for file_detail in file_input.file_details:
        file = file_detail.file
        file_name = file.filename
        content_type = file.content_type or "application/octet-stream"

        # Create S3 key with user_id/project_id/file_name structure
        s3_key = (
            f"{file_input.user_id}/{file_input.project_id}/{upload_type}/{file_name}"
        )

        # Upload file to S3
        s3_url = await s3_upload(
            file_name=s3_key,
            file_content=file_detail.contents,
            content_type=content_type,
        )

        if s3_url:
            # Add file information to file_info
            file_info.files.append(
                UploadedFile(file_name=file_name, s3_key=s3_key, file_description="", document_category="other")
            )
            uploaded_files.append(UploadedFileInfo(file_name=file_name, s3_url=s3_url))

    # Save file_info to MongoDB
    await file_info.save()

    return UploadFileOutput(
        status="success",
        message=f"Successfully uploaded {len(uploaded_files)} files",
        files=uploaded_files
    )


async def get_user_files(file_input: GetFilesInput) -> GetFilesOutput:
    """
    Retrieve files from MongoDB for a specific user and project

    Args:
        file_input: GetFilesInput object containing user_id and project_id

    Returns:
        GetFilesOutput object containing status, message, and files
    """
    logger.info(f"Retrieving files for user {file_input.user_id} and project {file_input.project_id}")

    # Find FileInfo document for the user and project
    file_info = await FileInfo.find_one(
        {"user_id": file_input.user_id, "project_id": file_input.project_id}
    )

    if not file_info:
        return GetFilesOutput(
            status="error",
            message=f"No files found for user {file_input.user_id} and project {file_input.project_id}",
            files=[]
        )

    # Extract file information
    files = [
        FileInfoSchema(
            file_name=file.file_name,
            s3_key=file.s3_key,
            file_description=file.file_description,
            document_category=file.document_category
        )
        for file in file_info.files
    ]

    return GetFilesOutput(
        status="success",
        message=f"Found {len(files)} files",
        files=files
    )


async def update_file_description(
    user_id: str,
    project_id: str,
    update_input: UpdateFileDescriptionInput
) -> UpdateFileDescriptionOutput:
    """
    Update file description for a specific file

    Args:
        user_id: ID of the user
        project_id: ID of the project
        update_input: UpdateFileDescriptionInput object containing s3_key and file_description

    Returns:
        UpdateFileDescriptionOutput object containing status, message, and updated file
    """
    logger.info(f"Updating file description for user {user_id} and project {project_id}")

    # Find FileInfo document for the user and project
    file_info = await FileInfo.find_one(
        {"user_id": user_id, "project_id": project_id}
    )

    if not file_info:
        return UpdateFileDescriptionOutput(
            status="error",
            message=f"No files found for user {user_id} and project {project_id}",
            file=None
        )

    # Find the file with the specified s3_key
    file_found = False
    updated_file = None

    for file in file_info.files:
        if file.s3_key == update_input.s3_key:
            file.file_description = update_input.file_description
            file.document_category = update_input.document_category
            file_found = True
            updated_file = FileInfoSchema(
                file_name=file.file_name,
                s3_key=file.s3_key,
                file_description=file.file_description,
                document_category=file.document_category
            )
            break

    if not file_found:
        return UpdateFileDescriptionOutput(
            status="error",
            message=f"File with s3_key {update_input.s3_key} not found",
            file=None
        )

    # Save the updated FileInfo document
    await file_info.save()

    return UpdateFileDescriptionOutput(
        status="success",
        message="File description updated successfully",
        file=updated_file
    )
