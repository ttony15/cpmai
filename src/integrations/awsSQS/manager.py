import json
from loguru import logger

from src.core.settings import settings
from src.integrations.awsSQS.client import get_client


async def send_message(message_body):
    try:
        async with get_client() as sqs:
            response = await sqs.send_message(
                QueueUrl=settings.sqs_queue_url, MessageBody=json.dumps(message_body)
            )
            return response
    except Exception as e:
        logger.error(f"Error sending message to SQS: {e}")
        return None
