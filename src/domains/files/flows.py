from loguru import logger

from src.domains.files.schemas import (
    FileInput,
    GetFilesInput,
    GetFilesOutput,
    FileInfo as FileInfoSchema,
    UploadFileOutput,
    UploadedFileInfo,
    UpdateFileDescriptionInput,
    UpdateFileDescriptionOutput,
)
from src.domains.files.models import UploadedFile
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

    # We no longer need to get or create FileInfo document
    # as we're using UploadedFile for everything

    uploaded_files = []

    # Upload each file to S3 and create UploadedFile documents
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
            # Create and save UploadedFile document
            uploaded_file = UploadedFile(
                file_name=file_name,
                s3_key=s3_key,
                user_id=file_input.user_id,
                project_id=file_input.project_id,
                file_description="",
                document_category="other",
            )
            await uploaded_file.save()

            uploaded_files.append(UploadedFileInfo(file_name=file_name, s3_url=s3_url))

    return UploadFileOutput(
        status="success",
        message=f"Successfully uploaded {len(uploaded_files)} files",
        files=uploaded_files,
    )


async def get_user_files(file_input: GetFilesInput) -> GetFilesOutput:
    """
    Retrieve files from MongoDB for a specific user and project

    Args:
        file_input: GetFilesInput object containing user_id and project_id

    Returns:
        GetFilesOutput object containing status, message, and files
    """
    logger.info(
        f"Retrieving files for user {file_input.user_id} and project {file_input.project_id}"
    )

    # Find all UploadedFile documents for the user and project
    uploaded_files = await UploadedFile.find(
        {"user_id": file_input.user_id, "project_id": file_input.project_id}
    ).to_list()

    if not uploaded_files:
        return GetFilesOutput(
            status="error",
            message=f"No files found for user {file_input.user_id} and project {file_input.project_id}",
            files=[],
        )

    # Extract file information
    files = [
        FileInfoSchema(
            file_name=file.file_name,
            s3_key=file.s3_key,
            file_description=file.file_description,
            document_category=file.document_category,
        )
        for file in uploaded_files
    ]

    return GetFilesOutput(
        status="success", message=f"Found {len(files)} files", files=files
    )


async def update_file_description(
    user_id: str, project_id: str, update_input: UpdateFileDescriptionInput
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
    logger.info(
        f"Updating file description for user {user_id} and project {project_id}"
    )

    # Find the UploadedFile document with the specified user_id, project_id, and s3_key
    uploaded_file = await UploadedFile.find_one({
        "user_id": user_id, 
        "project_id": project_id,
        "s3_key": update_input.s3_key
    })

    if not uploaded_file:
        return UpdateFileDescriptionOutput(
            status="error",
            message=f"File with s3_key {update_input.s3_key} not found for user {user_id} and project {project_id}",
            file=None,
        )

    # Update the file description and category
    uploaded_file.file_description = update_input.file_description
    uploaded_file.document_category = update_input.document_category

    # Save the updated UploadedFile document
    await uploaded_file.save()

    # Create the response object
    updated_file = FileInfoSchema(
        file_name=uploaded_file.file_name,
        s3_key=uploaded_file.s3_key,
        file_description=uploaded_file.file_description,
        document_category=uploaded_file.document_category,
    )

    return UpdateFileDescriptionOutput(
        status="success",
        message="File description updated successfully",
        file=updated_file,
    )
