from openai import AsyncOpenAI

from src.core.settings import settings


async def get_client():
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    return client
