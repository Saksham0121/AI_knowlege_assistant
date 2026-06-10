"""
Gemini Embedding Service using text-embedding-004 model.
Handles single and batch embeddings with retry logic.
"""
import asyncio
import logging
from typing import List, Optional
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "models/gemini-embedding-2"
BATCH_SIZE = 20  # Gemini API batch limit
MAX_RETRIES = 3
RETRY_DELAY = 2.0


class GeminiEmbedder:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)

    async def embed_text(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """Embed a single text string."""
        for attempt in range(MAX_RETRIES):
            try:
                result = await asyncio.to_thread(
                    genai.embed_content,
                    model=EMBEDDING_MODEL,
                    content=text,
                    task_type=task_type,
                )
                return result["embedding"]
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"Embedding failed after {MAX_RETRIES} retries: {e}")
                    raise
                logger.warning(f"Embedding attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
        return []

    async def embed_query(self, query: str) -> List[float]:
        """Embed a user query (uses retrieval_query task type for better matching)."""
        return await self.embed_text(query, task_type="retrieval_query")

    async def embed_batch(self, texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
        """
        Embed a list of texts in batches to respect API limits.
        Returns list of embedding vectors in same order as input.
        """
        all_embeddings = []

        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            batch_embeddings = []

            for text in batch:
                embedding = await self.embed_text(text, task_type)
                batch_embeddings.append(embedding)
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.05)

            all_embeddings.extend(batch_embeddings)
            logger.info(f"Embedded batch {i // BATCH_SIZE + 1}/{(len(texts) - 1) // BATCH_SIZE + 1}")

        return all_embeddings
