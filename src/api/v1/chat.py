from typing import List, Optional, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from domains.chat.schemas import ChatRequest
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
    """ Endpoint to fetch previous chats of a projects from auth id"""
    return await chat_flows.get_project_chats(project_id)

@chat_router.post(
    "/{project_id}",
    operation_id="api.chat.ask",
    summary="Endpoint to ask new chats"
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


@chat_router.post(
    "{project_id}/upload",
    operation_id="api.chat.upload_and_ask",
    summary="Endpoint to upload files and send chats",
)
async def upload(
    query: str = Form(...),
    files: List[UploadFile] = File(...),
    file_type: str = Form("document"),  # 'quote', 'drawing', 'spec', or 'document'
    auth: Any = Depends(verify_jwt),
):
    """
    Endpoint to upload files and ask a question

    - **query**: The text question or chat
    - **files**: List of files to upload (PDFs, specs, drawings, etc.)
    - **file_type**: Type of uploaded files (quote, drawing, spec, document)
    """
    user_id = auth["sub"]

    # Convert to the domain input schema
    chat_input = chat_schemas.ChatInput(
        user_id=user_id,
        query=query,
        project_id=project_id,
        files=files,
        file_type=file_type,
    )
    return await chat_flows.upload_file(chat_input)


