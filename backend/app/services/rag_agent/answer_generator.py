"""
Gemini-based answer generation for the RAG pipeline.

Uses Gemini API instead of Ollama or Groq.
"""

import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

ANSWER_PROMPT = """You are a knowledgeable assistant that answers questions \
based on the provided context documents. Follow these rules strictly:

1. Use ONLY information found in the context documents below.
2. You may summarize, explain, and infer conclusions that are clearly \
supported by the context.
3. Always cite your sources using the format: [Source: <filename>, Page: <page_number>]
4. If multiple documents contribute to the answer, cite all relevant sources.
5. Be concise but thorough in your response.
6. Do not use any outside knowledge.
7. Only reply with:

   "I could not find this information in the provided documents."

   if the context is completely unrelated to the question.

Context Documents:
{context}

Question:
{query}

Answer:"""


def generate_answer(
    query: str,
    context: str,
    gemini_api_key: str,
    model_name: str = "models/gemini-2.5-flash",
    temperature: float = 0.0,
) -> str:
    """Generate an answer from retrieved context using Gemini API.

    Args:
        query: The user's original question.
        context: Formatted context string from retrieved documents.
        gemini_api_key: Gemini API key.
        model_name: Gemini model to use.
        temperature: Sampling temperature (default 0 for deterministic output).

    Returns:
        Generated answer string.

    Raises:
        Exception: On connection failures (propagated to caller).
    """
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel(model_name)

    prompt = ANSWER_PROMPT.format(context=context, query=query)
    
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=temperature)
    )
    answer = response.text.strip()

    logger.info(
        "Answer generated via Gemini (%s) — %d chars",
        model_name,
        len(answer),
    )
    return answer
