"""
RAG chain orchestration — Gemini edition.

Provides the same public interface (build_rag_chain / run_rag_chain /
build_general_chain / run_general_chain) so agent.py needs no changes.
Uses Gemini API instead of Ollama.
"""

import logging
from typing import Any, Dict, List, Tuple
import google.generativeai as genai
from langchain_core.documents import Document

from app.services.rag_agent.answer_generator import generate_answer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context formatting (moved here from retriever.py for chain ownership)
# ---------------------------------------------------------------------------


def format_retrieved_context(results: List[Tuple[Document, float]]) -> str:
    """Format retrieved documents into a context string for the LLM.

    Args:
        results: List of (Document, score) tuples from retrieval/reranking.

    Returns:
        Formatted string with numbered document blocks and source citations.
    """
    if not results:
        return "No relevant documents found."

    parts = []
    for i, (doc, score) in enumerate(results, 1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "N/A")
        chunk_id = doc.metadata.get("chunk_id", "N/A")
        parts.append(
            f"[Document {i}]\n"
            f"Source: {source}\n"
            f"Page: {page}\n"
            f"Chunk ID: {chunk_id}\n"
            f"Relevance Score: {score:.4f}\n"
            f"Content:\n{doc.page_content}\n"
        )
    return "\n---\n".join(parts)


# ---------------------------------------------------------------------------
# RAG chain
# ---------------------------------------------------------------------------


def build_rag_chain(config: Any) -> Dict[str, str]:
    """Build the RAG chain configuration object.

    Args:
        config: RAGConfig instance containing Gemini API key and model name.

    Returns:
        Chain config dict consumed by run_rag_chain.
    """
    chain: Dict[str, str] = {
        "gemini_api_key": config.gemini_api_key,
        "model_name": config.gemini_model_name,
    }
    logger.info("RAG chain built successfully (Gemini model: %s)", config.gemini_model_name)
    return chain


def run_rag_chain(
    chain: Dict[str, str],
    question: str,
    retrieved_results: List[Tuple[Document, float]],
) -> Dict[str, Any]:
    """Execute the RAG chain with retrieved (and reranked) context.

    Args:
        chain: Chain config from build_rag_chain.
        question: The user's original question.
        retrieved_results: List of (Document, score) tuples — already
                           reranked by the calling agent.

    Returns:
        Dictionary containing:
            - answer (str): Generated answer with source citations
            - sources (list): Source citation dicts
            - num_sources (int): Number of source documents used
            - question (str): Original question
    """
    logger.info("Running RAG chain for question: '%s'", question[:100])

    context = format_retrieved_context(retrieved_results)

    answer = generate_answer(
        query=question,
        context=context,
        gemini_api_key=chain["gemini_api_key"],
        model_name=chain["model_name"],
    )

    sources = []
    for doc, score in retrieved_results:
        sources.append(
            {
                "source": doc.metadata.get("source", "unknown"),
                "page": doc.metadata.get("page", 0),
                "chunk_id": doc.metadata.get("chunk_id", "N/A"),
                "relevance_score": round(float(score), 4),
                "content_preview": doc.page_content[:200],
            }
        )

    result = {
        "answer": answer,
        "sources": sources,
        "num_sources": len(sources),
        "question": question,
    }

    logger.info(
        "RAG chain completed — answer: %d chars, sources: %d",
        len(answer),
        len(sources),
    )
    return result


# ---------------------------------------------------------------------------
# General / fallback chain (no document context)
# ---------------------------------------------------------------------------

GENERAL_SYSTEM_PROMPT = (
    "You are a helpful general-knowledge assistant. Follow these rules:\n"
    "1. Answer using your general knowledge only.\n"
    "2. Do NOT reference private documents, uploaded files, or confidential information.\n"
    "3. If you are unsure about the answer, say so honestly.\n"
    "4. Keep answers concise and informative.\n"
    "5. Do NOT fabricate specific document references, page numbers, or citations."
)

GENERAL_USER_PROMPT = (
    "Question: {question}\n\n"
    "Please provide a helpful answer based on your general knowledge."
)


def build_general_chain(config: Any) -> Dict[str, str]:
    """Build the general-knowledge LLM chain (no document context).

    Args:
        config: RAGConfig instance with Gemini settings.

    Returns:
        Chain config dict consumed by run_general_chain.
    """
    chain: Dict[str, str] = {
        "gemini_api_key": config.gemini_api_key,
        "model_name": config.gemini_model_name,
    }
    logger.info("General LLM chain built successfully (Gemini)")
    return chain


def run_general_chain(chain: Dict[str, str], question: str) -> Dict[str, Any]:
    """Execute the general LLM chain without document context using Gemini.

    Args:
        chain: Chain config from build_general_chain.
        question: User question.

    Returns:
        Dictionary with answer, empty sources list, and source_type='general_llm'.
    """
    logger.info("Running general LLM chain for question: '%s'", question[:100])

    genai.configure(api_key=chain["gemini_api_key"])
    model = genai.GenerativeModel(chain["model_name"])
    
    prompt = f"{GENERAL_SYSTEM_PROMPT}\n\n{GENERAL_USER_PROMPT.format(question=question)}"
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.3)
    )
    answer = response.text.strip()

    result = {
        "answer": answer,
        "sources": [],
        "num_sources": 0,
        "question": question,
        "source_type": "general_llm",
    }

    logger.info(
        "General LLM chain completed — answer: %d chars", len(answer)
    )
    return result
