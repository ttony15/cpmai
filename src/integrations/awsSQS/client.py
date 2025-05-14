from contextlib import asynccontextmanager

from aiobotocore.session import get_session
from src.core.settings import settings

@asynccontextmanager
async def get_client():
    session = get_session()
    async with session.create_client(
        "sqs",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key,
        aws_secret_access_key=settings.aws_secret_key,
    ) as client:
        yield client