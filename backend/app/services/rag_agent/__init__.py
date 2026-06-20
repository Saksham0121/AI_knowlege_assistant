"""
RAG Agent - Retrieval-Augmented Generation Agent

A production-grade RAG agent that uses Ollama for embeddings and LLM,
FAISS for vector storage, and LangChain for orchestration.
"""

from app.services.rag_agent.agent import RAGAgent
from app.services.rag_agent.config import RAGConfig

__version__ = "0.1.0"
__all__ = ["RAGAgent", "RAGConfig"]
