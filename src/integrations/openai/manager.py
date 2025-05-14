from typing import AsyncIterator
import io

from loguru import logger
from openai.types.chat import ChatCompletionChunk

from src.core.settings import settings
from src.integrations.openai.client import get_client


async def openai_complete(prompt):
    client = await get_client()

    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]
    response = await client.chat.completions.create(
        messages=messages,
        model="gpt-4o-mini",
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


async def finetune_model(
    jsonl_training_data: str, model: str = "gpt-4o-mini-2024-07-18"
):
    """
    Finetune a model with the provided training data
    :param jsonl_training_data: JSONL string containing the training data
    :param model: The base model to finetune
    :return: The fine-tuning job details
    """
    try:
        logger.info("[OPENAI MANAGER] Finetuning")
        logger.debug(f"[OPENAI MANAGER] {model}")
        client = await get_client()

        # Create a file-like object from the JSONL string
        bytes_data = jsonl_training_data.encode("utf-8")
        file_obj = io.BytesIO(bytes_data)

        # Upload the training data directly from memory
        file_response = await client.files.create(file=file_obj, purpose="fine-tune")

        # Create a fine-tuning job
        job_response = await client.fine_tuning.jobs.create(
            training_file=file_response.id, model=model
        )

        logger.info(f"Fine-tuning job created: {job_response.id}")
        return job_response
    except Exception as e:
        logger.error(f"Error in finetune_model: {e}")
        raise e
