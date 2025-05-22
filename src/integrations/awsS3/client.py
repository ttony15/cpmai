from contextlib import asynccontextmanager

from aiobotocore.session import get_session

from src.core.settings import settings


@asynccontextmanager
async def get_client():
    session = get_session()
    async with session.create_client(
        "s3",
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    ) as client:
        yield client
