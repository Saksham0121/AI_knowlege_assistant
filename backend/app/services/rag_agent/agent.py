"""
High-level RAG Agent interface — advanced pipeline edition.

Orchestrates the full pipeline:
  1. Guardrails       — block off-topic queries early
  2. Query rewriting  — LLM improves the query for better retrieval
  3. Hybrid retrieval — FAISS (semantic) + BM25 (keyword) fusion
  4. Reranking        — CrossEncoder selects the best chunks
  5. Generation       — Ollama produces the final answer with citations

Ingestion and vectorstore persistence remain unchanged.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document

from app.services.rag_agent.chain import (
    build_general_chain,
    build_rag_chain,
    run_general_chain,
    run_rag_chain,
)
from app.services.rag_agent.config import RAGConfig
from app.services.rag_agent.embeddings import check_embeddings_health, create_embeddings
from app.services.rag_agent.guardrails import route_query
from app.services.rag_agent.hybrid_retriever import hybrid_retrieve
from app.services.rag_agent.keyword_extractor import extract_keywords, load_keywords, save_keywords
from app.services.rag_agent.query_rewriter import rewrite_query
from app.services.rag_agent.reranker import load_reranker, rerank_documents
from app.services.rag_agent.vectorstore import (
    add_documents,
    create_vectorstore,
    get_vectorstore_info,
    load_vectorstore,
    save_vectorstore,
)

logger = logging.getLogger(__name__)


class RAGAgent:
    """High-level RAG (Retrieval-Augmented Generation) Agent.

    Orchestrates document ingestion, embedding generation, vector storage,
    hybrid retrieval, cross-encoder reranking, and Ollama-powered answer
    generation with source citations.

    Usage:
        >>> from rag_agent import RAGAgent, RAGConfig
        >>> config = RAGConfig.from_env()
        >>> agent = RAGAgent(config)
        >>> agent.ingest(documents)
        >>> result = agent.query("What is the penalty for data breach?")
        >>> print(result["answer"])
        >>> print(result["sources"])
    """

    def __init__(self, config: Optional[RAGConfig] = None):
        """Initialize the RAG Agent with the advanced pipeline.

        Args:
            config: RAG configuration. If None, loads from environment.
        """
        self.config = config or RAGConfig.from_env()

        logger.info("Initializing RAG Agent (advanced pipeline)")

        # Embedding model (SentenceTransformers)
        self._embeddings = create_embeddings(self.config)

        # Local LLM chains
        self._chain = build_rag_chain(self.config)
        self._general_chain = build_general_chain(self.config)

        # CrossEncoder reranker — loaded once at startup
        self._reranker = load_reranker(self.config.reranker_model_name)

        # Vector store
        self._vectorstore = None
        self._try_load_vectorstore()

        # Keywords for dynamic routing
        self._keywords = load_keywords(self.config.faiss_index_path)

        logger.info("RAG Agent initialized successfully")

    # ------------------------------------------------------------------
    # Vector store management
    # ------------------------------------------------------------------

    def _try_load_vectorstore(self) -> None:
        """Attempt to load an existing vector store from disk."""
        existing = load_vectorstore(
            self.config.faiss_index_path,
            self._embeddings,
        )
        if existing:
            self._vectorstore = existing
            info = get_vectorstore_info(existing)
            logger.info(
                "Loaded existing vector store: %d vectors, %d dimensions",
                info["total_vectors"],
                info["dimension"],
            )
        else:
            logger.info("No existing vector store found — ready for ingestion")

    def ingest(
        self,
        documents: List[Document],
        save: bool = True,
    ) -> Dict[str, Any]:
        """Ingest documents into the vector store.

        Takes preprocessed LangChain Document objects, generates embeddings,
        and stores them in the FAISS vector store.

        Args:
            documents: List of LangChain Document objects with metadata:
                - source (str): Source filename
                - page (int): Page number
                - chunk_id (str): Unique chunk identifier
            save: Whether to persist the vector store to disk.

        Returns:
            Dictionary with ingestion statistics.

        Raises:
            ValueError: If documents list is empty.
        """
        if not documents:
            raise ValueError("Cannot ingest empty document list")

        logger.info("Ingesting %d documents", len(documents))

        if self._vectorstore is None:
            self._vectorstore = create_vectorstore(documents, self._embeddings)
        else:
            add_documents(self._vectorstore, documents)

        if save:
            self.config.ensure_index_directory()
            save_vectorstore(self._vectorstore, self.config.faiss_index_path)
            
            # Update and save keywords
            new_keywords = extract_keywords(documents)
            
            # Combine while preserving order (newest/most frequent first)
            # dict.fromkeys() is O(N) fast like a set, but preserves order (Python 3.7+)
            self._keywords = list(dict.fromkeys(new_keywords + self._keywords))
            
            save_keywords(self._keywords, self.config.faiss_index_path)

        info = get_vectorstore_info(self._vectorstore)

        result = {
            "status": "success",
            "documents_ingested": len(documents),
            "total_vectors": info["total_vectors"],
            "dimension": info["dimension"],
            "index_path": self.config.faiss_index_path,
        }

        logger.info(
            "Ingestion complete: %d docs ingested, %d total vectors",
            len(documents),
            info["total_vectors"],
        )
        return result

    # ------------------------------------------------------------------
    # Query — full advanced pipeline
    # ------------------------------------------------------------------

    def query(self, question: str, department: str = None) -> Dict[str, Any]:
        """Query the RAG agent using the advanced pipeline.

        Pipeline steps:
          1. Guardrails       — reject off-topic queries immediately
          2. Query rewriting  — Ollama rewrites the query for better retrieval
          3. Hybrid retrieval — FAISS + BM25 with metadata boosting
          4. Reranking        — CrossEncoder picks top-k from candidates
          5. Generation       — Ollama generates the answer with citations

        Args:
            question: User question string.

        Returns:
            Dictionary containing:
                - answer (str): Generated answer with inline citations
                - sources (list): Source citation dicts
                - num_sources (int): Number of sources used
                - question (str): Original question
                - rewritten_query (str): Query after rewriting (may equal question)
                - source_type (str): Always 'rag'

        Raises:
            RuntimeError: If no vector store is available.
        """
        if self._vectorstore is None:
            raise RuntimeError(
                "No vector store available. Please ingest documents first "
                "using agent.ingest(documents)"
            )

        logger.info("Processing query: '%s'", question[:100])

        # ---- 1. Dynamic Routing / Guardrails ------------------------------
        route, message = route_query(
            query=question,
            stored_keywords=self._keywords,
            gemini_api_key=self.config.gemini_api_key,
            model_name=self.config.gemini_model_name,
        )

        if route == "BLOCK":
            logger.info("Query blocked by router/guardrails")
            return {
                "answer": message,
                "sources": [],
                "num_sources": 0,
                "question": question,
                "rewritten_query": question,
                "source_type": "guardrail",
            }
            
        if route == "LLM":
            logger.info("Router directed query to general LLM chain")
            return run_general_chain(self._general_chain, message)

        # ---- 2. Query rewriting -------------------------------------------
        rewritten = rewrite_query(
            question,
            gemini_api_key=self.config.gemini_api_key,
            model_name=self.config.gemini_model_name,
        )

        # ---- 3. Hybrid FAISS + BM25 retrieval ----------------------------
        hybrid_results = hybrid_retrieve(
            vectorstore=self._vectorstore,
            query=rewritten,
            top_k_retrieval=self.config.top_k_retrieval,
            metadata_bonus=self.config.metadata_bonus,
            department=department,
        )

        if not hybrid_results:
            logger.warning("No documents retrieved for query")
            return {
                "answer": (
                    "I don't have enough information in the provided "
                    "documents to answer this question."
                ),
                "sources": [],
                "num_sources": 0,
                "question": question,
                "rewritten_query": rewritten,
                "source_type": "rag",
            }

        # ---- 4. CrossEncoder reranking ------------------------------------
        candidate_docs = [doc for doc, _ in hybrid_results]
        reranked = rerank_documents(
            query=rewritten,
            documents=candidate_docs,
            reranker=self._reranker,
            top_k=self.config.top_k_context,
        )

        # ---- 5. Ollama answer generation ------------------------------------
        result = run_rag_chain(
            chain=self._chain,
            question=question,
            retrieved_results=reranked,
        )
        result["source_type"] = "rag"
        result["rewritten_query"] = rewritten

        return result

    def smart_query(self, question: str, department: str = None) -> Dict[str, Any]:
        """Query using the advanced RAG pipeline, falling back to Ollama general LLM.

        Falls back when:
          - No vector store exists (no documents ingested)
          - RAG pipeline finds no answer in context

        Args:
            question: User question string.

        Returns:
            Dictionary with answer, sources, and source_type ('rag' or 'general_llm').
        """
        try:
            result = self.query(question, department=department)
            answer_lower = result["answer"].lower()

            insufficient_phrases = [
                "don't have enough information",
                "do not have enough information",
                "could not find this information",
                "i cannot find",
            ]
            if any(p in answer_lower for p in insufficient_phrases):
                logger.info(
                    "RAG context insufficient — falling back to general Ollama LLM"
                )
                return run_general_chain(self._general_chain, question)

            return result

        except RuntimeError:
            logger.info("No vector store — using general Ollama LLM")
            return run_general_chain(self._general_chain, question)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self) -> Dict[str, Any]:
        """Check health of all RAG Agent components.

        Returns:
            Dictionary with status for embeddings, groq_llm, vectorstore,
            and an overall status.
        """
        logger.info("Running health check")

        # Embeddings health
        emb_health = check_embeddings_health(self._embeddings)

        # Gemini health
        gemini_health = self._check_gemini_health()

        # Vectorstore health
        vs_health = self._get_vectorstore_health()

        component_statuses = [emb_health["status"], gemini_health["status"]]

        if all(s == "healthy" for s in component_statuses):
            overall = "healthy"
        elif any(s == "healthy" for s in component_statuses):
            overall = "degraded"
        else:
            overall = "unhealthy"

        health = {
            "embeddings": emb_health,
            "local_llm": gemini_health,
            "vectorstore": vs_health,
            "overall": overall,
        }

        logger.info("Health check complete — overall: %s", overall)
        return health

    def _check_gemini_health(self) -> dict:
        """Ping Gemini to verify API key is working."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.config.gemini_api_key)
            model = genai.GenerativeModel(self.config.gemini_model_name)
            model.generate_content("ping")
            return {
                "status": "healthy",
                "model": self.config.gemini_model_name,
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini health check failed: %s", exc)
            return {
                "status": "unhealthy",
                "error": str(exc),
            }

    def _get_vectorstore_health(self) -> dict:
        """Get vector store health status."""
        if self._vectorstore is None:
            return {
                "status": "not_initialized",
                "message": "No documents have been ingested yet",
            }

        info = get_vectorstore_info(self._vectorstore)
        return {
            "status": "healthy",
            "total_vectors": info["total_vectors"],
            "dimension": info["dimension"],
            "index_path": self.config.faiss_index_path,
        }

    # ------------------------------------------------------------------
    # Properties / stats
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """True if a vector store is loaded with documents."""
        return self._vectorstore is not None

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics.

        Returns:
            Dictionary with agent configuration and store info.
        """
        stats = {
            "config": {
                "gemini_model": self.config.gemini_model_name,
                "embed_model": self.config.embed_model_name,
                "reranker_model": self.config.reranker_model_name,
                "top_k_retrieval": self.config.top_k_retrieval,
                "top_k_context": self.config.top_k_context,
                "metadata_bonus": self.config.metadata_bonus,
            },
            "is_ready": self.is_ready,
        }

        if self._vectorstore:
            stats["vectorstore"] = get_vectorstore_info(self._vectorstore)

        return stats
