from typing import Literal, Any

from fastapi import APIRouter, Depends

from src.dependencies.auth.auth import verify_jwt
import src.domains.user.flows as user_flows
import src.domains.user.schemas as user_schemas

report_router = APIRouter(tags=["Report"])


@report_router.get(
    "/generate/{project_id}/{tone}/",
    operation_id="api.report.generate",
    summary="Endpoint to generate report",
)
async def generate_report(
    project_id: str,
    tone: str = Literal["executive", "instructional"],
    auth: Any = Depends(verify_jwt),
):
    """
    Endpoint to generate report
    """
    user_id = auth["sub"]
    if tone:
        await user_flows.persist_writer_mode(
            user_schemas.WriterModeIn(
                user_id=user_id,
                tone=tone,
            )
        )
    else:
        stored = user_flows.fetch_writer_mode(user_id)
        selected = stored if stored in PROMPT_TEMPLATES else "executive"
