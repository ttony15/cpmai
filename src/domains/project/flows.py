import datetime
import zoneinfo
import uuid
from loguru import logger
from typing import List, Optional, Tuple

from src.domains.project.models import Project
from src.domains.project.schemas import ProjectCreate, ProjectUpdate


async def create_project(user_id: str, project_data: ProjectCreate) -> Project:
    """
    Create a new project in the database.

    Args:
        user_id: The ID of the user creating the project
        project_data: The data for the new project

    Returns:
        The created Project document
    """
    try:
        # Generate a unique project ID
        project_id = str(uuid.uuid4())

        # Create a new project
        project = Project(
            project_id=project_id,
            user_id=user_id,
            name=project_data.name,
            description=project_data.description,
            status="created"
        )

        # Save the project to the database
        await project.save()
        logger.info(f"Created new project with ID: {project_id} for user: {user_id}")
        return project

    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise


async def get_project(user_id: str, project_id: str) -> Optional[Project]:
    """
    Get a project by ID.

    Args:
        user_id: The ID of the user requesting the project
        project_id: The ID of the project to retrieve

    Returns:
        The Project document if found, None otherwise
    """
    try:
        # Find the project by project_id and user_id
        project = await Project.find_one({"project_id": project_id, "user_id": user_id})
        return project

    except Exception as e:
        logger.error(f"Error retrieving project {project_id}: {e}")
        raise


async def get_projects(user_id: str, page: int = 1, page_size: int = 5) -> Tuple[List[Project], int]:
    """
    Get all projects for a user with pagination.

    Args:
        user_id: The ID of the user
        page: The page number (1-indexed)
        page_size: The number of items per page

    Returns:
        A tuple of (list of Project documents, total count)
    """
    try:
        # Calculate skip for pagination
        skip = (page - 1) * page_size

        # Find all projects for the user with pagination
        projects = await Project.find({"user_id": user_id}).skip(skip).limit(page_size).to_list()

        # Get total count of projects for the user
        total = await Project.find({"user_id": user_id}).count()

        return projects, total

    except Exception as e:
        logger.error(f"Error retrieving projects for user {user_id}: {e}")
        raise


async def update_project(user_id: str, project_id: str, project_data: ProjectUpdate) -> Optional[Project]:
    """
    Update a project in the database.

    Args:
        user_id: The ID of the user updating the project
        project_id: The ID of the project to update
        project_data: The data to update the project with

    Returns:
        The updated Project document if found, None otherwise
    """
    try:
        # Find the project by project_id and user_id
        project = await Project.find_one({"project_id": project_id, "user_id": user_id})

        if not project:
            logger.warning(f"Project {project_id} not found for user {user_id}")
            return None

        # Update the project fields if provided
        if project_data.name is not None:
            project.name = project_data.name
        if project_data.description is not None:
            project.description = project_data.description
        if project_data.status is not None:
            project.status = project_data.status

        # Update the updated_at timestamp
        project.updated_at = datetime.datetime.now(tz=zoneinfo.ZoneInfo("UTC"))

        # Save the updated project to the database
        await project.save()
        logger.info(f"Updated project {project_id} for user {user_id}")
        return project

    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}")
        raise


async def update_project_status(user_id: str, project_id: str, status: str) -> Project:
    """
    Update the status of a project in the database.

    Args:
        user_id: The ID of the user updating the project
        project_id: The ID of the project to update
        status: The new status of the project (created, in_progress, completed, failed)

    Returns:
        The updated Project document
    """
    try:
        # Find the project by project_id
        project = await Project.find_one({"project_id": project_id})

        if not project:
            # If project doesn't exist, create a new one
            logger.info(
                f"Creating new project with ID: {project_id} and status: {status}"
            )
            project = Project(
                project_id=project_id,
                user_id=user_id,
                name=f"Project {project_id}",  # Default name
                status=status,
            )
        else:
            # Update the existing project
            logger.info(f"Updating project {project_id} status to: {status}")
            project.status = status
            project.updated_at = datetime.datetime.now(tz=zoneinfo.ZoneInfo("UTC"))

        # Save the project to the database
        await project.save()
        return project

    except Exception as e:
        logger.error(f"Error updating project status: {e}")
        raise
