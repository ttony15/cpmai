from typing import AsyncIterator

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from src.domains.chat.schemas import ChatRequest
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
async def ask_chat(
    project_id: str,
    request: ChatRequest,
) -> StreamingResponse:
    """Endpoint to ask new chats
    - **query**: the query to ask new chats
    - **project_id**: the project id of the current user which is optional
    """
    user_id = "test_user_id"
    chat_input = chat_schemas.ChatInput(
        user_id=user_id,
        query=request.query,
        project_id=project_id,
        files=None,
    )

    async def formatted_response() -> AsyncIterator[str]:
        async for chunk in chat_flows.chat(chat_input):
            yield chunk

    return StreamingResponse(
        content=formatted_response(),
        media_type="application/x-ndjson",
    )
