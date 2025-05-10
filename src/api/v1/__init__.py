from fastapi import APIRouter

from src.api.v1.hearbeat import heartbeat_router
from src.api.v1.report import report_router

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(heartbeat_router)
v1_router.include_router(report_router, prefix='/report', )
