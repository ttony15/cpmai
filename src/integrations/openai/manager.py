from typing import AsyncIterator

from loguru import logger
from openai.types.chat import ChatCompletionChunk

from src.core.settings import settings
from src.integrations.openai.client import get_client


async def openai_complete(prompt, file=None):
    client = await get_client()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
            ],
        }
    ]

    if file:
        messages[0]["content"].append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{file}"},
            }
        )

    response = await client.chat.completions.create(
        messages=messages,
        model="gpt-4-turbo",
        stream=False,
    )
    return response.choices[0].message.content


async def llm_stream(
    prompt: str,
) -> AsyncIterator[str]:
    """
    Unified LLM completion function similar to utils.py
    """
    openai_client = await get_client()
    stream = await openai_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o",
        temperature=0.7,
        stream=True,
    )
    async for chunk in stream:
        if isinstance(chunk, ChatCompletionChunk):
            if chunk.choices:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content


async def create_embeddings(context: str):
    """
    Create embeddings of text
    :param context:
    :return:
    """
    try:
        client = await get_client()
        response = await client.embeddings.create(
            input=context,
            model=settings.openai_embedding_model,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error in create_embeddings: {e}")
        return []
