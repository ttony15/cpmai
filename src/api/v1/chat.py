from typing import Any
from fastapi import APIRouter, Depends

from src.domains.chat.schemas import ChatRequest
from src.dependencies.auth.auth import verify_jwt
import src.domains.chat.flows as chat_flows
import src.domains.chat.schemas as chat_schemas

chat_router = APIRouter(tags=["chat"])


@chat_router.get(
    "/{project_id}",
    operation_id="api.chat.get",
    summary="Endpoint to fetch previous projects from auth id",
)
async def get_chats(
    project_id: str,
):
    """Endpoint to fetch previous chats of a projects from auth id"""
    return await chat_flows.get_project_chats(project_id)


@chat_router.post(
    "/{project_id}", operation_id="api.chat.ask", summary="Endpoint to ask new chats"
)
async def ask_chat(request: ChatRequest, auth: Any = Depends(verify_jwt)):
    """Endpoint to ask new chats
    - **query**: the query to ask new chats
    - **project_id**: the project id of the current user which is optional
    """
    user_id = auth["sub"]
    chat_input = chat_schemas.ChatInput(
        user_id=user_id, query=request.query, project_id=request.project_id, files=None
    )
    return await chat_flows.process_chat(chat_input)
