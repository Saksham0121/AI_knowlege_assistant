"""
CrossEncoder-based document reranking.

After hybrid retrieval fetches ~10 candidate chunks, the CrossEncoder
re-scores every (query, chunk) pair and keeps only the top-k.
This dramatically improves precision without hurting recall.
"""

import logging
from typing import List, Tuple

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


def load_reranker(model_name: str) -> CrossEncoder:
    """Load the CrossEncoder reranker model from HuggingFace.

    Args:
        model_name: HuggingFace model identifier
                    (e.g. 'cross-encoder/ms-marco-MiniLM-L-6-v2').

    Returns:
        Loaded CrossEncoder model instance.
    """
    logger.info("Loading CrossEncoder reranker: %s", model_name)
    reranker = CrossEncoder(model_name)
    logger.info("CrossEncoder reranker loaded successfully")
    return reranker


def rerank_documents(
    query: str,
    documents: List[Document],
    reranker: CrossEncoder,
    top_k: int = 5,
) -> List[Tuple[Document, float]]:
    """Rerank documents using a CrossEncoder model.

    Scores each (query, document_text) pair and returns the
    top_k highest-scoring documents.

    Args:
        query: User query string (after rewriting).
        documents: Candidate documents from hybrid retrieval.
        reranker: Loaded CrossEncoder model.
        top_k: Number of top documents to return after reranking.

    Returns:
        List of (Document, rerank_score) tuples, sorted descending by score.
    """
    if not documents:
        return []

    pairs = [(query, doc.page_content) for doc in documents]
    raw_scores = reranker.predict(pairs)

    # Convert numpy floats to plain Python floats
    scores = [float(s) for s in raw_scores]

    reranked = sorted(
        zip(documents, scores),
        key=lambda x: x[1],
        reverse=True,
    )

    top = reranked[:top_k]

    logger.info(
        "Reranked %d candidates → top %d  (best=%.4f, worst=%.4f)",
        len(documents),
        len(top),
        top[0][1] if top else 0.0,
        top[-1][1] if top else 0.0,
    )

    return top
