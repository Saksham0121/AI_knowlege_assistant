"""
LLM initialization using Ollama.

Provides functions to initialize and configure ChatOllama
for answer generation in the RAG pipeline.
"""

import logging

from langchain_ollama import ChatOllama

from app.services.rag_agent.config import RAGConfig

logger = logging.getLogger(__name__)


def create_llm(config: RAGConfig) -> ChatOllama:
    """Create a ChatOllama LLM instance from configuration.

    Args:
        config: RAG configuration containing Ollama LLM settings.

    Returns:
        Configured ChatOllama instance.
    """
    logger.info(
        "Initializing ChatOllama (model=%s, base_url=%s, temperature=%.2f)",
        config.ollama_llm_model,
        config.ollama_base_url,
        config.llm_temperature,
    )

    llm = ChatOllama(
        model=config.ollama_llm_model,
        base_url=config.ollama_base_url,
        temperature=config.llm_temperature,
        top_p=config.llm_top_p,
        num_ctx=config.llm_num_ctx,
    )

    logger.info("ChatOllama initialized successfully")
    return llm


def check_llm_health(llm: ChatOllama) -> dict:
    """Check if the Ollama LLM service is reachable and functional.

    Args:
        llm: Configured ChatOllama instance.

    Returns:
        Dictionary with health status and details.
    """
    try:
        response = llm.invoke("Say 'OK' if you are working.")
        return {
            "status": "healthy",
            "model": llm.model,
            "response_preview": str(response.content)[:100],
        }
    except Exception as e:
        logger.error("LLM health check failed: %s", e)
        return {
            "status": "unhealthy",
            "model": llm.model,
            "error": str(e),
        }
