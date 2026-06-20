"""
Document retrieval using FAISS similarity search.

Wraps FAISS vector store as a LangChain retriever with
configurable top-k and score threshold filtering.
"""

import logging
from typing import List, Tuple

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.services.rag_agent.config import RAGConfig

logger = logging.getLogger(__name__)


def create_retriever(
    vectorstore: FAISS,
    config: RAGConfig,
):
    """Create a LangChain retriever from a FAISS vector store.

    Args:
        vectorstore: FAISS vector store instance.
        config: RAG configuration with retriever settings.

    Returns:
        LangChain retriever instance.
    """
    logger.info(
        "Creating retriever (top_k=%d, score_threshold=%.2f)",
        config.retriever_top_k,
        config.retriever_score_threshold,
    )

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": config.retriever_top_k,
        },
    )

    return retriever


def retrieve_with_scores(
    vectorstore: FAISS,
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.0,
) -> List[Tuple[Document, float]]:
    """Retrieve documents with their similarity scores.

    Args:
        vectorstore: FAISS vector store instance.
        query: User query string.
        top_k: Number of top results to return.
        score_threshold: Minimum similarity score (lower is better for L2 distance).

    Returns:
        List of (Document, score) tuples, sorted by relevance.
    """
    logger.info("Retrieving documents for query: '%s'", query[:100])

    results = vectorstore.similarity_search_with_score(query, k=top_k)

    # Filter by score threshold if set (FAISS uses L2 distance — lower = more similar)
    if score_threshold > 0:
        results = [(doc, score) for doc, score in results if score <= score_threshold]

    logger.info(
        "Retrieved %d documents (scores: %s)",
        len(results),
        [f"{score:.4f}" for _, score in results],
    )

    for doc, score in results:
        logger.debug(
            "  - [%.4f] %s (page %s, chunk %s): %s...",
            score,
            doc.metadata.get("source", "unknown"),
            doc.metadata.get("page", "?"),
            doc.metadata.get("chunk_id", "?"),
            doc.page_content[:80],
        )

    return results


def format_retrieved_context(results: List[Tuple[Document, float]]) -> str:
    """Format retrieved documents into a context string for the LLM.

    Each document is formatted with its source citation and content.

    Args:
        results: List of (Document, score) tuples from retrieval.

    Returns:
        Formatted context string with source citations.
    """
    if not results:
        return "No relevant documents found."

    context_parts = []
    for i, (doc, score) in enumerate(results, 1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "N/A")
        chunk_id = doc.metadata.get("chunk_id", "N/A")

        context_parts.append(
            f"[Document {i}]\n"
            f"Source: {source}\n"
            f"Page: {page}\n"
            f"Chunk ID: {chunk_id}\n"
            f"Relevance Score: {score:.4f}\n"
            f"Content:\n{doc.page_content}\n"
        )

    return "\n---\n".join(context_parts)
