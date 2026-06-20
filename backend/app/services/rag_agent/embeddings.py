"""
Embedding model initialization using Gemini.

Replaces HuggingFace embeddings with Gemini's text-embedding-004 model.
"""

import logging
from typing import List
import google.generativeai as genai
from langchain_core.embeddings import Embeddings

from app.services.rag_agent.config import RAGConfig

logger = logging.getLogger(__name__)


class GeminiLangchainEmbeddings(Embeddings):
    """Custom LangChain Embeddings wrapper for Gemini."""

    def __init__(self, api_key: str, model_name: str):
        genai.configure(api_key=api_key)
        self.model_name = model_name

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # For simplicity and rate limit robustness, we process sequentially, 
        # but in production, batching using genai.embed_content with a list of contents is better.
        try:
            # The python SDK accepts a list of strings for content
            results = genai.embed_content(
                model=self.model_name, 
                content=texts, 
                task_type="retrieval_document"
            )
            if isinstance(results["embedding"], list) and len(results["embedding"]) > 0 and isinstance(results["embedding"][0], list):
                return results["embedding"]
            elif isinstance(results["embedding"], list):
                 # Single response case
                 return [results["embedding"]]
        except Exception as e:
            logger.error("Failed to batch embed documents: %s", e)
            
            # Fallback to sequential
            result_list = []
            for text in texts:
                res = genai.embed_content(
                    model=self.model_name, 
                    content=text, 
                    task_type="retrieval_document"
                )
                result_list.append(res["embedding"])
            return result_list
        return []

    def embed_query(self, text: str) -> List[float]:
        res = genai.embed_content(
            model=self.model_name, 
            content=text, 
            task_type="retrieval_query"
        )
        return res["embedding"]


def create_embeddings(config: RAGConfig) -> Embeddings:
    """Create a Gemini embedding model wrapper.

    Args:
        config: RAGConfig instance.

    Returns:
        Embeddings instance compatible with LangChain FAISS.
    """
    logger.info("Initializing Gemini embeddings (model=%s)", config.embed_model_name)
    embeddings = GeminiLangchainEmbeddings(api_key=config.gemini_api_key, model_name=config.embed_model_name)
    logger.info("Gemini embeddings initialized successfully")
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
            "model": getattr(embeddings, "model_name", "gemini-embeddings"),
            "dimension": len(test_vec),
        }
    except Exception as exc:
        logger.error("Embeddings health check failed: %s", exc)
        return {
            "status": "unhealthy",
            "error": str(exc),
        }
