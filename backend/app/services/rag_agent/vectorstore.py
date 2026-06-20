"""
FAISS vector store management.

Provides functions to create, save, load, and update FAISS
vector stores for document retrieval.
"""

import logging
from pathlib import Path
from typing import List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.services.rag_agent.config import RAGConfig

logger = logging.getLogger(__name__)


def create_vectorstore(
    documents: List[Document],
    embeddings: Embeddings,
) -> FAISS:
    """Create a new FAISS vector store from documents.

    Args:
        documents: List of LangChain Document objects with page_content
                   and metadata (source, page, chunk_id).
        embeddings: Embedding model for vectorizing documents.

    Returns:
        FAISS vector store instance.

    Raises:
        ValueError: If documents list is empty.
    """
    if not documents:
        raise ValueError("Cannot create vector store from empty document list")

    logger.info("Creating FAISS vector store from %d documents", len(documents))

    # Validate metadata on documents
    for i, doc in enumerate(documents):
        if not doc.metadata.get("source"):
            logger.warning(
                "Document %d missing 'source' metadata, setting to 'unknown'", i
            )
            doc.metadata.setdefault("source", "unknown")
        doc.metadata.setdefault("page", 0)
        doc.metadata.setdefault("chunk_id", str(i))

    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embeddings,
    )

    logger.info(
        "FAISS vector store created with %d vectors",
        vectorstore.index.ntotal,
    )
    return vectorstore


def save_vectorstore(vectorstore: FAISS, path: str) -> None:
    """Save FAISS vector store to disk.

    Args:
        vectorstore: FAISS vector store instance.
        path: Directory path to save the index and docstore.
    """
    save_path = Path(path)
    save_path.mkdir(parents=True, exist_ok=True)

    vectorstore.save_local(str(save_path))
    logger.info("Vector store saved to %s (%d vectors)", save_path, vectorstore.index.ntotal)


def load_vectorstore(path: str, embeddings: Embeddings) -> Optional[FAISS]:
    """Load a FAISS vector store from disk.

    Args:
        path: Directory path containing the saved index.
        embeddings: Embedding model (must match the one used during creation).

    Returns:
        FAISS vector store instance, or None if path doesn't exist.
    """
    load_path = Path(path)

    if not load_path.exists():
        logger.warning("Vector store path does not exist: %s", load_path)
        return None

    index_file = load_path / "index.faiss"
    if not index_file.exists():
        logger.warning("No FAISS index found at: %s", load_path)
        return None

    logger.info("Loading vector store from %s", load_path)

    vectorstore = FAISS.load_local(
        str(load_path),
        embeddings,
        allow_dangerous_deserialization=True,
    )

    logger.info(
        "Vector store loaded with %d vectors",
        vectorstore.index.ntotal,
    )
    return vectorstore


def add_documents(
    vectorstore: FAISS,
    documents: List[Document],
) -> None:
    """Add new documents to an existing FAISS vector store.

    Args:
        vectorstore: Existing FAISS vector store.
        documents: New documents to add.
    """
    if not documents:
        logger.warning("No documents to add")
        return

    logger.info("Adding %d documents to vector store", len(documents))

    # Ensure metadata defaults
    for i, doc in enumerate(documents):
        doc.metadata.setdefault("source", "unknown")
        doc.metadata.setdefault("page", 0)
        doc.metadata.setdefault("chunk_id", str(i))

    vectorstore.add_documents(documents)

    logger.info(
        "Vector store now contains %d vectors",
        vectorstore.index.ntotal,
    )


def get_vectorstore_info(vectorstore: FAISS) -> dict:
    """Get information about the vector store.

    Args:
        vectorstore: FAISS vector store instance.

    Returns:
        Dictionary with vector store statistics.
    """
    return {
        "total_vectors": vectorstore.index.ntotal,
        "dimension": vectorstore.index.d,
    }
