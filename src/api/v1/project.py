from fastapi import APIRouter, Query

project_router = APIRouter(tags=["Project"])

@project_router.get(
    "/",
    operation_id="api.projects.list",
    summary="List all auth user's projects",
)
async def get_projects(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=5, ge=1),
):
    """ Get all auth user's projects"""
    return await get_projects(page, page_size)

@project_router.post(
    "/",
    operation_id="api.projects.create",
    summary="Create a new auth user's project",
)
async def create_project():
    """ Create a new auth user's project"""
    return await create_project()

@project_router.get(
    "/{project_id}",
    operation_id="api.projects.get",
    summary="Get a specific auth user's project",
)
async def get_project(
        project_id: str,
):
    """Get a specific auth user's project"""
    return await get_project(project_id)

@project_router.put(
    "/{project_id}",
    operation_id="api.projects.update",
    summary="Update a specific auth user's project",
)
async def update_project(
        project_id: str,
):
    """Update a specific auth user's project"""
    return await update_project()

@project_router.delete(
    "/{project_id}",
)
async def delete_project():
    """Delete a specific auth user's project"""
    return await delete_project()