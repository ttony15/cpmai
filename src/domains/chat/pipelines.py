from src.domains.chat.schemas import ChatInput


async def chat_pipeline(query_embedding, context: ChatInput):
    """
    create mongodb pipeline
    """
    pipeline = [
        {
            "$vectorSearch": {
                "index": "file_index",
                "path": "files.embeddings",
                "queryVector": query_embedding,
                "numCandidates": 150,
                "limit": 100,
            }
        },
        {
            "$match": {
                "user_id": context.user_id,
                "project_id": context.project_id,
            }
        },
    ]
    return pipeline
