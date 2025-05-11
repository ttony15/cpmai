from loguru import logger

from src.core.settings import settings
from src.integrations.awsS3.client import get_client


async def download(file_url):
    try:
        # Extract the key (filename) from the S3 URL
        file_name = file_url.split("/")[-1]

        async with get_client() as s3:
            response = await s3.get_object(Bucket=settings.s3_bucket, Key=file_name)
            return response["Body"].read().decode("utf-8")
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return None


async def upload(file_name, file_content, content_type):
    try:
        async with get_client() as s3:
            await s3.put_object(
                Bucket=settings.s3_bucket,
                Key=file_name,
                Body=file_content,
                ContentType=content_type,
            )
            return f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com/{file_name}"
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return None
