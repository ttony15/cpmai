from fastapi import APIRouter, Query, Body, HTTPException, status
from loguru import logger
import datetime

from src.integrations.awsSQS.manager import send_message
from src.domains.project.flows import (
    update_project_status,
    create_project as create_project_flow,
    get_project as get_project_flow,
    get_projects as get_projects_flow,
    update_project as update_project_flow,
)
from src.domains.project.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
)

project_router = APIRouter(tags=["Project"])


@project_router.get(
    "/",
    operation_id="api.projects.list",
    summary="List all auth user's projects",
    response_model=ProjectListResponse,
)
async def get_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=1),
):
    """Get all auth user's projects"""
    user_id = "test_user_id"  # TODO: Get user id from jwt

    try:
        # Get projects for the user with pagination
        projects, total = await get_projects_flow(user_id, page, page_size)

        # Convert to response model
        project_responses = [
            ProjectResponse(
                project_id=project.project_id,
                user_id=project.user_id,
                name=project.name,
                description=project.description,
                status=project.status,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            for project in projects
        ]

        # Return the response
        return ProjectListResponse(
            total=total, page=page, page_size=page_size, projects=project_responses
        )
    except Exception as e:
        logger.error(f"Error getting projects for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve projects",
        )


@project_router.post(
    "/",
    operation_id="api.projects.create",
    summary="Create a new auth user's project",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(project_data: ProjectCreate = Body(...)):
    """Create a new auth user's project"""
    user_id = "test_user_id"  # TODO: Get user id from jwt

    try:
        # Create the project
        project = await create_project_flow(user_id, project_data)

        # Return the response
        return ProjectResponse(
            project_id=project.project_id,
            user_id=project.user_id,
            name=project.name,
            description=project.description,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
    except Exception as e:
        logger.error(f"Error creating project for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project",
        )


@project_router.get(
    "/{project_id}",
    operation_id="api.projects.get",
    summary="Get a specific auth user's project",
    response_model=ProjectResponse,
)
async def get_project(
    project_id: str,
):
    """Get a specific auth user's project"""
    user_id = "test_user_id"  # TODO: Get user id from jwt

    try:
        # Get the project
        project = await get_project_flow(user_id, project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found",
            )

        # Return the response
        return ProjectResponse(
            project_id=project.project_id,
            user_id=project.user_id,
            name=project.name,
            description=project.description,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project",
        )


@project_router.put(
    "/{project_id}",
    operation_id="api.projects.update",
    summary="Update a specific auth user's project",
    response_model=ProjectResponse,
)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate = Body(...),
):
    """Update a specific auth user's project"""
    user_id = "test_user_id"  # TODO: Get user id from jwt

    try:
        # Update the project
        project = await update_project_flow(user_id, project_id, project_data)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found",
            )

        # Return the response
        return ProjectResponse(
            project_id=project.project_id,
            user_id=project.user_id,
            name=project.name,
            description=project.description,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project {project_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project",
        )


@project_router.delete(
    "/{project_id}",
)
async def delete_project():
    """Delete a specific auth user's project"""
    user_id = "test_user_id"  # TODO: Get user id from jwt


@project_router.post(
    "/{project_id}/process",
    operation_id="api.projects.process",
    summary="Send the project files to SQL to process the project",
)
async def process_project(project_id: str):
    """Process the project files to SQL to process the project"""
    user_id = "test_user_id"
    try:
        # Save the project ID and set status as in_progress in the database
        await update_project_status(
            user_id=user_id, project_id=project_id, status="in_progress"
        )
        logger.info(f"Project status updated to in_progress: {project_id}")

        message = {
            "project_id": project_id,
            "user_id": user_id,
            "action": "process",
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        }

        sqs_response = await send_message(message)

        if sqs_response:
            logger.info(f"Project sent to processing queue: {project_id}")
            return {
                "status": "success",
                "message": f"Project {project_id} submitted for processing",
            }
        else:
            logger.error(f"Failed to send project to SQS: {project_id}")
            return {
                "status": "error",
                "message": "Failed to submit project for processing",
            }
    except Exception as e:
        logger.error(f"Error processing project {project_id}: {e}")
        return {"status": "error", "message": str(e)}
