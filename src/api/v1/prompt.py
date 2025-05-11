from typing import List, Optional, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from src.dependencies.auth.auth import verify_jwt
import src.domains.prompt.flows as prompt_flows
import src.domains.prompt.schemas as prompt_schemas


prompt_router = APIRouter(prefix="/prompts", tags=["prompt"])


# TODO: Move all schemas to schemas file.
class PromptRequest(BaseModel):
    query: str
    project_id: Optional[str] = None


class PromptResponse(BaseModel):
    response: str
    sources: List[dict] = []
    file_ids: List[str] = []


@prompt_router.get(
    "/",
    operation_id="api.prompt.get",
    summary="Endpoint to fetch previous prompts from auth id",
)
async def get_prompts():
    return {"prompts": ["prompt1", "prompt2"]}


@prompt_router.post(
    "/", operation_id="api.prompt.ask", summary="Endpoint to ask new prompts"
)
async def ask_prompt(request: PromptRequest, auth: Any = Depends(verify_jwt)):
    """Endpoint to ask new prompts
    - **query**: the query to ask new prompts
    - **project_id**: the project id of the current user which is optional
    """
    user_id = auth["sub"]
    prompt_input = prompt_schemas.PromptInput(
        user_id=user_id, query=request.query, project_id=request.project_id, files=None
    )

    try:
        result = await prompt_flows.process_prompt(prompt_input)

        return {
            "status": "ok",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process prompt: {str(e)}"
        )


@prompt_router.post(
    "/upload",
    operation_id="api.prompt.upload_and_ask",
    summary="Endpoint to upload files and send prompts",
    response_model=PromptResponse,
)
async def upload_and_ask(
    query: str = Form(...),
    files: List[UploadFile] = File(...),
    project_id: Optional[str] = Form(None),
    file_type: str = Form("document"),  # 'quote', 'drawing', 'spec', or 'document'
    auth: Any = Depends(verify_jwt),
):
    """
    Endpoint to upload files and ask a question

    - **query**: The text question or prompt
    - **files**: List of files to upload (PDFs, specs, drawings, etc.)
    - **project_id**: Optional project ID to associate with this query
    - **file_type**: Type of uploaded files (quote, drawing, spec, document)
    """
    user_id = auth["sub"]

    # Convert to the domain input schema
    prompt_input = prompt_schemas.PromptInput(
        user_id=user_id,
        query=query,
        project_id=project_id,
        files=files,
        file_type=file_type,
    )

    try:
        # Pass to domain layer
        result = await prompt_flows.process_prompt(prompt_input)

        return PromptResponse(
            response=result.response, sources=result.sources, file_ids=result.file_ids
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process prompt: {str(e)}"
        )
