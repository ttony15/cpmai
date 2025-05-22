from typing import AsyncIterator

import orjson

from src.domains.chat.pipelines import chat_pipeline
from src.domains.chat.schemas import ChatInput

import src.integrations.openai.manager as ai_manager
import src.domains.files.models as file_models


async def semantic_search(context: ChatInput):
    """Semantic search for relevant chunks"""
    query_embeddings = await ai_manager.generate_embeddings(context.query)
    pipeline = await chat_pipeline(query_embeddings, context)

    results = []

    async for doc in file_models.FileInfo.aggregate(pipeline):
        doc.pop("_id", None)
        for file in doc["files"]:
            file.pop("embeddings", None)
        results.append(doc)
    return results


async def chat(context: ChatInput) -> AsyncIterator[str]:
    """Main flow for processing a chat with project details"""

    matches = await semantic_search(context)

    prompt = f"""
    Your role is to act as a helpful AI assistant. Please answer the user's question using only the information 
    provided below. If the answer isn't in the provided text, simply state that you don't have enough 
    information to answer. Please do not make up any details. Respond back in markdown format.
    
    Information: {orjson.dumps(matches, option=orjson.OPT_INDENT_2).decode("utf-8")}
    User query: {context.query}
    """

    async for chunk in ai_manager.llm_stream(prompt):
        yield chunk
