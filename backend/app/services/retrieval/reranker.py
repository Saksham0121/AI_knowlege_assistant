"""
Reranking layer — uses Gemini to reorder retrieved chunks by relevance.
Provides more accurate ranking than vector similarity alone.
"""
import asyncio
import logging
import json
from typing import List
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_CHUNKS_TO_RERANK = 10


class GeminiReranker:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def rerank(self, query: str, chunks: List[dict]) -> List[dict]:
        """
        Rerank chunks by relevance to the query using Gemini.
        Returns chunks sorted by reranking score (highest first).
        """
        if not chunks:
            return chunks

        # Only rerank top N to keep latency low
        to_rerank = chunks[:MAX_CHUNKS_TO_RERANK]
        remaining = chunks[MAX_CHUNKS_TO_RERANK:]

        # Build the prompt
        chunks_text = "\n\n".join(
            f"[{i}] {chunk['text'][:300]}"  # truncate for prompt
            for i, chunk in enumerate(to_rerank)
        )

        prompt = f"""You are a relevance scoring assistant.

Rate how relevant each passage is to the question on a scale of 0-10.

Question: "{query}"

Passages:
{chunks_text}

Return ONLY a JSON array of scores (numbers 0-10) in the SAME ORDER as the passages.
Example: [8, 3, 9, 1, 7]

Scores:"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=100,
                ),
            )

            text = response.text.strip()
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                scores = json.loads(text[start:end])
                if isinstance(scores, list) and len(scores) == len(to_rerank):
                    # Apply reranking scores
                    for i, chunk in enumerate(to_rerank):
                        chunk["rerank_score"] = float(scores[i]) / 10.0
                    to_rerank.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
                    logger.info(f"Reranked {len(to_rerank)} chunks for query: {query[:50]}")
                    return to_rerank + remaining

        except Exception as e:
            logger.warning(f"Reranking failed, using original order: {e}")

        # Fallback: return original order
        return chunks
