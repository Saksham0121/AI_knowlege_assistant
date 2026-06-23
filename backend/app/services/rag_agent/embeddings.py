"""
Embedding model initialization using HuggingFace.

Replaces Gemini embeddings with open-source HuggingFace models.
"""

import logging
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings

from app.services.rag_agent.config import RAGConfig

logger = logging.getLogger(__name__)


def create_embeddings(config: RAGConfig) -> Embeddings:
    """Create a HuggingFace embedding model wrapper.

    Args:
        config: RAGConfig instance.

    Returns:
        Embeddings instance compatible with LangChain FAISS.
    """
    logger.info("Initializing HuggingFace embeddings (model=%s)", config.embed_model_name)
    # Use HuggingFace embeddings
    embeddings = HuggingFaceEmbeddings(model_name=config.embed_model_name)
    logger.info("HuggingFace embeddings initialized successfully")
    return embeddings


def check_embeddings_health(embeddings: Embeddings) -> dict:
    """Check that the embedding model is operational.

    Args:
        embeddings: Embeddings instance.

    Returns:
        Health status dict with 'status', 'model', and 'dimension' keys.
    """
    try:
        test_vec = embeddings.embed_query("health check")
        return {
            "status": "healthy",
            "model": getattr(embeddings, "model_name", "huggingface-embeddings"),
            "dimension": len(test_vec),
        }
    except Exception as exc:
        logger.error("Embeddings health check failed: %s", exc)
        return {
            "status": "unhealthy",
            "error": str(exc),
        }
