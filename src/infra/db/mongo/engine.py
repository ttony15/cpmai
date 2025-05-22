import asyncio

from beanie import init_beanie
from motor.core import AgnosticClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient

from src.core.settings import settings


def get_client() -> AgnosticClient:
    """Get the MongoDB client."""

    # https://stackoverflow.com/questions/41584243/runtimeerror-task-attached-to-a-different-loop
    loop = asyncio.get_event_loop()
    if loop is None:
        loop = asyncio.new_event_loop()

    client = AsyncIOMotorClient(
        str(settings.mongodb_uri),
        tlsAllowInvalidCertificates=True,
        io_loop=loop,
        tz_aware=True,
    )
    client.get_io_loop = asyncio.get_running_loop
    return client


def get_sync_client() -> MongoClient:
    """Get the MongoDB client."""

    client = MongoClient(
        str(settings.mongodb_uri),
        tlsAllowInvalidCertificates=True,
    )

    return client


def get_database(db_name: str | None = None) -> AsyncIOMotorDatabase:  # type: ignore
    """"""
    client = get_client()
    if db_name is None:
        return client.get_default_database()
    return client.get_database(db_name)


async def init_beanine_db(database_name: str | None = None, document_models=[]):
    database = get_database(database_name)

    from src.domains.train.models import TrainFiles, TrainedModel
    from src.domains.files.models import FileInfo
    from src.domains.project.models import Project
    from src.domains.files.models import UploadedFile

    await init_beanie(
        database,
        document_models=[
            # Import and provide mongoDB models here.
            TrainFiles,
            TrainedModel,
            FileInfo,
            Project,
            UploadedFile,
        ],
    )


# async def setup_search_indexes():
#     client = get_client()
#     db = client.get_default_database()
#     search_index_model = SearchIndexModel(
#         definition={
#             "fields": [
#                 {
#                     "type": "vector",
#                     "numDimensions": 1536,
#                     "path": "embeddings",
#                     "similarity": "cosine",
#                 }
#             ]
#         },
#         name="default",
#         type="vectorSearch",
#     )
#
#     try:
#         if "RecordsModel" not in await db.list_collection_names():
#             await db.create_collection("RecordsModel")
#         await db["RecordsModel"].create_search_index(model=search_index_model)
#         async for index_info in db["RecordsModel"].list_search_indexes():
#             logger.info(f"Found index: {index_info}")
#             return
#     except Exception as e:
#         logger.error(e)
#         return
