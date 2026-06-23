"""
LLM-based query rewriting using Gemini.

Rewrites user queries before retrieval to improve recall —
e.g., expanding abbreviations, clarifying ambiguous terms.
Falls back gracefully to the original query on any failure.
"""

import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

QUERY_REWRITE_PROMPT = """You are a query rewriting assistant for a legal document RAG system.

Rules:
1. Preserve the user's original terminology whenever possible.
2. Rewrite only if it genuinely improves retrieval (e.g., expand abbreviations, clarify vague terms).
3. Do NOT introduce new laws, regulations, organizations, or concepts not implied by the original.
4. Do NOT answer the question — only rewrite it.
5. If the query is already clear and specific, return it completely unchanged.
6. Return ONLY the rewritten query — no explanation, no prefix.

User Query:
{query}
"""


def rewrite_query(
    query: str,
    gemini_api_key: str,
    model_name: str = "models/gemini-2.5-flash",
    **kwargs,
) -> str:
    """Rewrite a user query using Gemini LLM for better retrieval.

    Args:
        query: Original user query string.
        gemini_api_key: API key for Gemini.
        model_name: Gemini model name.

    Returns:
        Rewritten query string, or the original query if rewriting fails.
    """
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel(model_name)
        
        prompt = QUERY_REWRITE_PROMPT.format(query=query)
        
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0)
        )
        rewritten = response.text.strip()

        if rewritten and rewritten != query:
            logger.info(
                "Query rewritten: '%s' → '%s'",
                query[:80],
                rewritten[:80],
            )
        else:
            logger.info("Query unchanged after rewriting: '%s'", query[:80])

        return rewritten or query

    except Exception as exc:
        logger.warning(
            "Query rewriting failed (%s) — using original query", exc
        )
        return query
