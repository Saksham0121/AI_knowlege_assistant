"""
Query Expansion using Gemini — expands user query into related terms
to improve recall during retrieval.
"""
import logging
import json
import asyncio
from typing import List
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryExpander:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def expand(self, query: str) -> List[str]:
        """
        Generate related search terms and alternative phrasings for the query.
        Returns a list of expanded query variants.
        """
        prompt = f"""You are a search query expansion assistant for an enterprise knowledge base.

Given the user's search query, generate 4-5 alternative phrasings or related terms that would help retrieve relevant documents.

User query: "{query}"

Return ONLY a JSON array of strings with the expanded queries. No explanation.
Example format: ["term1", "term2", "alternative phrasing", "related concept"]

Return the JSON array now:"""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=200,
                ),
            )

            text = response.text.strip()
            # Extract JSON array
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                expanded = json.loads(text[start:end])
                if isinstance(expanded, list):
                    logger.info(f"Query expanded: '{query}' → {expanded}")
                    return [str(e) for e in expanded[:5]]

        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")

        # Fallback: return original query only
        return [query]
