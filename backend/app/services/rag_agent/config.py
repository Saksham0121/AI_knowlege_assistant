"""
Configuration management for the RAG Agent.

Loads settings from environment variables and .env file,
providing sensible defaults for all parameters.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """Configuration for the RAG Agent.

    Loads from environment variables with fallback defaults.
    Can also be instantiated directly with explicit values.

    Attributes:
        # ---- Ollama (kept for embeddings health checks / legacy) ----
        ollama_base_url: Base URL for Ollama API server.
        ollama_llm_model: Ollama LLM model name (kept for reference).
        ollama_embed_model: Ollama embedding model (legacy — now overridden
                            by embed_model_name when SentenceTransformers is used).

        # ---- Embeddings (SentenceTransformers) ----
        embed_model_name: HuggingFace model for document & query embeddings.

        # ---- Groq LLM ----
        groq_api_key: Groq Cloud API key.
        groq_model_name: Groq model for query rewriting & answer generation.

        # ---- Reranker ----
        reranker_model_name: CrossEncoder model for post-retrieval reranking.

        # ---- FAISS ----
        faiss_index_path: Directory path for persisting the FAISS index.

        # ---- Retriever settings ----
        retriever_top_k: (legacy) top-k for plain FAISS retrieval.
        retriever_score_threshold: Minimum similarity score threshold.
        top_k_retrieval: Candidates pulled from each retriever (FAISS + BM25).
        top_k_context: Final chunks sent to LLM after reranking.
        metadata_bonus: Extra score added for metadata-matched docs.

        # ---- LLM parameters ----
        llm_temperature: Sampling temperature (kept for reference).
        llm_top_p: Nucleus sampling parameter.
        llm_num_ctx: Context window size in tokens.

        # ---- Logging ----
        log_level: Logging verbosity level.
    """

    # ---- Gemini API Configuration ----
    gemini_api_key: str = ""
    gemini_model_name: str = "gemini-1.5-flash"
    embed_model_name: str = "models/text-embedding-004"

    # Reranker
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # FAISS
    faiss_index_path: str = "./vectorstore"

    # Retriever (legacy)
    retriever_top_k: int = 5
    retriever_score_threshold: float = 0.0

    # Advanced retrieval
    top_k_retrieval: int = 10   # candidates from FAISS + BM25 each
    top_k_context: int = 5      # reranked chunks sent to LLM
    metadata_bonus: float = 0.2

    # LLM parameters
    llm_temperature: float = 0.1
    llm_top_p: float = 0.9
    llm_num_ctx: int = 4096

    # Logging
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env_path: str | None = None) -> "RAGConfig":
        """Create configuration from environment variables.

        Args:
            env_path: Optional path to .env file. If None, searches
                      current directory and parent directories.

        Returns:
            RAGConfig instance populated from environment variables.
        """
        load_dotenv(dotenv_path=env_path)

        # Fix macOS OpenMP conflict between FAISS and conda/numpy
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

        config = cls(
            # Gemini Settings
            gemini_api_key=os.getenv("GEMINI_API_KEY", cls.gemini_api_key),
            gemini_model_name=os.getenv("GEMINI_MODEL_NAME", cls.gemini_model_name),
            embed_model_name=os.getenv("EMBEDDING_MODEL_NAME", cls.embed_model_name),

            # Reranker
            reranker_model_name=os.getenv(
                "RERANKER_MODEL_NAME", cls.reranker_model_name
            ),

            # FAISS
            faiss_index_path=os.getenv("FAISS_INDEX_PATH", cls.faiss_index_path),

            # Retriever
            retriever_top_k=int(
                os.getenv("RETRIEVER_TOP_K", str(cls.retriever_top_k))
            ),
            retriever_score_threshold=float(
                os.getenv(
                    "RETRIEVER_SCORE_THRESHOLD",
                    str(cls.retriever_score_threshold),
                )
            ),

            # Advanced retrieval
            top_k_retrieval=int(
                os.getenv("TOP_K_RETRIEVAL", str(cls.top_k_retrieval))
            ),
            top_k_context=int(
                os.getenv("TOP_K_CONTEXT", str(cls.top_k_context))
            ),
            metadata_bonus=float(
                os.getenv("METADATA_BONUS", str(cls.metadata_bonus))
            ),

            # LLM params
            llm_temperature=float(
                os.getenv("LLM_TEMPERATURE", str(cls.llm_temperature))
            ),
            llm_top_p=float(os.getenv("LLM_TOP_P", str(cls.llm_top_p))),
            llm_num_ctx=int(os.getenv("LLM_NUM_CTX", str(cls.llm_num_ctx))),

            # Logging
            log_level=os.getenv("LOG_LEVEL", cls.log_level),
        )

        config._configure_logging()
        logger.info("Configuration loaded successfully")
        logger.debug("Config: %s", config)

        return config

    def _configure_logging(self) -> None:
        """Configure logging based on the log_level setting."""
        numeric_level = getattr(logging, self.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def ensure_index_directory(self) -> Path:
        """Ensure the FAISS index directory exists.

        Returns:
            Path object for the index directory.
        """
        path = Path(self.faiss_index_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
