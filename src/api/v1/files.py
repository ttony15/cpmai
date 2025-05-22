from typing import List

from fastapi import APIRouter, UploadFile, File
import src.domains.files.schemas as file_schemas
import src.domains.files.flows as file_flows

files_router = APIRouter(tags=["files"])


@files_router.post(
    "/{project_id}/upload",
    operation_id="api.files.upload",
    summary="Endpoint to upload files",
    response_model=file_schemas.UploadFileOutput,
)
async def upload(
    project_id: str,
    files: List[UploadFile] = File(...),
):
    """
    Endpoint to upload files and ask a question
    - **files**: List of files to upload (PDFs, specs, drawings, etc.)

    Returns:
        UploadFileOutput containing status, message, and a list of uploaded files
    """
    user_id = "test_user_id"

    file_details = []
    for file in files:
        file_details.append(file_schemas.FileDetails(file=file))
    file_input = file_schemas.FileInput(
        user_id=user_id,
        project_id=project_id,
        file_details=file_details,
    )
    return await file_flows.upload_file(file_input)


@files_router.get(
    "/{project_id}/files",
    operation_id="api.files.get_files",
    summary="Endpoint to retrieve user files for a project",
    response_model=file_schemas.GetFilesOutput,
)
async def get_files(
    project_id: str,
):
    """
    Endpoint to retrieve files for a specific user and project
    - **project_id**: ID of the project

    Returns:
        GetFilesOutput containing status, message, and a list of files
    """
    user_id = (
        "test_user_id"  # In a real application, this would come from authentication
    )

    file_input = file_schemas.GetFilesInput(user_id=user_id, project_id=project_id)

    return await file_flows.get_user_files(file_input)


@files_router.patch(
    "/{project_id}/file-description",
    operation_id="api.files.update_file_description",
    summary="Endpoint to update file description",
    response_model=file_schemas.UpdateFileDescriptionOutput,
)
async def update_file_description(
    project_id: str,
    update_input: file_schemas.UpdateFileDescriptionInput,
):
    """
    Endpoint to update file description for a specific file
    - **project_id**: ID of the project
    - **update_input**: UpdateFileDescriptionInput containing s3_key, file_description, and document_category
                       (document_category can be: drawing, specification, quote, contract, schedule, other)

    Returns:
        UpdateFileDescriptionOutput containing status, message, and updated file
    """
    user_id = "test_user_id"  # TODO: Get user id from jwt

    return await file_flows.update_file_description(
        user_id=user_id, project_id=project_id, update_input=update_input
    )
