from fastapi import APIRouter

heartbeat_router = APIRouter(tags=["Heartbeat"])


@heartbeat_router.get(
    "/heartbeat/",
    operation_id="api.heartbeat.check",
    summary="Endpoint to get heartbeat",
)
async def heartbeat() -> dict:
    """
    Endpoint to test heartbeat
    """
    return {"status": "ok"}
