"""
Hybrid retrieval: FAISS semantic search + BM25 keyword search.

Combines the strengths of both:
  - FAISS captures semantic/conceptual matches
  - BM25 captures exact keyword/phrase matches (important for legal text)

A weighted score fusion merges both result sets, and optional
metadata boosting rewards docs whose filenames match the query topic.
"""

import logging
from typing import Dict, List, Tuple

import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metadata keyword map
# Maps a substring of the source filename → query keywords that should boost it.
# Extend this dict when you ingest new document types.
# ---------------------------------------------------------------------------
DOCUMENT_KEYWORDS: Dict[str, List[str]] = {
    "dpdp": [
        "data protection",
        "personal data",
        "data fiduciary",
        "data principal",
        "consent",
        "data breach",
        "dpdp",
        "privacy",
        "sensitive data",
    ],
    "financeact": [
        "finance act",
        "finance",
        "budget",
        "tax",
        "fiscal",
        "income tax",
        "gst",
        "customs",
        "excise",
        "revenue",
        "amendment",
        "surcharge",
        "cess",
    ],
    "itact": [
        "information technology",
        "it act",
        "cyber",
        "digital signature",
        "electronic",
        "computer",
        "internet",
        "network",
        "cybercrime",
        "hacking",
        "data theft",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_scores(scores: List[float]) -> List[float]:
    """Min-max normalize a list of scores to [0, 1]."""
    arr = np.array(scores, dtype=float)
    span = arr.max() - arr.min()
    if span == 0:
        return [1.0] * len(scores)
    return ((arr - arr.min()) / span).tolist()


def _metadata_boost(source: str, query_lower: str, bonus: float) -> float:
    """Return a score bonus if the source filename matches query keywords."""
    src = source.lower()
    for doc_key, keywords in DOCUMENT_KEYWORDS.items():
        if doc_key in src:
            for kw in keywords:
                if kw in query_lower:
                    return bonus
    return 0.0


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def _get_all_docs(vectorstore: FAISS) -> List[Document]:
    """Extract every document stored in the LangChain FAISS docstore."""
    return list(vectorstore.docstore._dict.values())


def _build_bm25(documents: List[Document]) -> BM25Okapi:
    """Build a BM25 index from a list of LangChain Documents."""
    corpus = [doc.page_content.lower().split() for doc in documents]
    return BM25Okapi(corpus)


def hybrid_retrieve(
    vectorstore: FAISS,
    query: str,
    top_k_retrieval: int = 10,
    faiss_weight: float = 0.7,
    bm25_weight: float = 0.3,
    metadata_bonus: float = 0.2,
    department: str = None,
) -> List[Tuple[Document, float]]:
    """Perform hybrid FAISS + BM25 retrieval with metadata boosting.

    Args:
        vectorstore: Existing LangChain FAISS vectorstore (already ingested).
        query: User query string (after optional rewriting).
        top_k_retrieval: Number of candidates to pull from each retriever.
        faiss_weight: Weight applied to normalised FAISS similarity scores.
        bm25_weight:  Weight applied to normalised BM25 scores.
        metadata_bonus: Extra score added when a doc's filename matches
                        known query keywords.

    Returns:
        List of (Document, fused_score) tuples sorted descending by score,
        truncated to top_k_retrieval entries.
    """
    logger.info("Hybrid retrieval — query: '%s'", query[:100])
    query_lower = query.lower()

    # ------------------------------------------------------------------
    # 1.  FAISS semantic search
    # ------------------------------------------------------------------
    filter_dict = {"department": department} if department else None
    faiss_results: List[Tuple[Document, float]] = (
        vectorstore.similarity_search_with_score(query, k=top_k_retrieval, filter=filter_dict)
    )

    if not faiss_results:
        logger.warning("FAISS returned 0 results — nothing to retrieve")
        return []

    # LangChain FAISS returns L2 distances (lower = more similar).
    # Convert to similarity: sim = 1 / (1 + distance), then normalise.
    faiss_raw_dists = [dist for _, dist in faiss_results]
    faiss_sim = [1.0 / (1.0 + d) for d in faiss_raw_dists]
    faiss_norm = _normalize_scores(faiss_sim)

    # ------------------------------------------------------------------
    # 2.  BM25 keyword search across ALL docs in the vectorstore
    # ------------------------------------------------------------------
    all_docs = _get_all_docs(vectorstore)
    if department:
        all_docs = [doc for doc in all_docs if doc.metadata.get("department") == department]

    if not all_docs:
        logger.warning(f"No documents found for department {department}")
        return []

    bm25 = _build_bm25(all_docs)
    tokenized_q = query_lower.split()
    bm25_all_scores = bm25.get_scores(tokenized_q)

    top_bm25_idx = np.argsort(bm25_all_scores)[::-1][:top_k_retrieval]
    bm25_docs = [all_docs[i] for i in top_bm25_idx]
    bm25_top_scores = bm25_all_scores[top_bm25_idx].tolist()
    bm25_norm = _normalize_scores(bm25_top_scores)

    # ------------------------------------------------------------------
    # 3.  Weighted score fusion
    #     Use first 150 chars of page_content as a deduplication key.
    # ------------------------------------------------------------------
    combined: Dict[str, Dict] = {}

    for (doc, _), norm in zip(faiss_results, faiss_norm):
        key = doc.page_content[:150]
        boost = _metadata_boost(
            doc.metadata.get("source", ""), query_lower, metadata_bonus
        )
        combined[key] = {"doc": doc, "score": faiss_weight * norm + boost}

    for doc, norm in zip(bm25_docs, bm25_norm):
        key = doc.page_content[:150]
        boost = _metadata_boost(
            doc.metadata.get("source", ""), query_lower, metadata_bonus
        )
        if key in combined:
            combined[key]["score"] += bm25_weight * norm
        else:
            combined[key] = {"doc": doc, "score": bm25_weight * norm + boost}

    # ------------------------------------------------------------------
    # 4.  Rank and return
    # ------------------------------------------------------------------
    ranked = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
    results = [(item["doc"], item["score"]) for item in ranked[:top_k_retrieval]]

    logger.info(
        "Hybrid retrieval: FAISS=%d, BM25=%d → merged=%d unique candidates",
        len(faiss_results),
        len(bm25_docs),
        len(combined),
    )

    return results
