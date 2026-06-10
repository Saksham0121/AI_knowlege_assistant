"""
Hybrid Search: merges semantic (ChromaDB cosine) + keyword (BM25) scores.
Final score = 0.7 * semantic_score + 0.3 * normalized_bm25_score
"""
import logging
from typing import List, Optional
from app.services.retrieval.vector_store import VectorStore
from app.services.retrieval.bm25_retriever import BM25Retriever
from app.services.embedding.gemini_embedder import GeminiEmbedder

logger = logging.getLogger(__name__)

SEMANTIC_WEIGHT = 0.7
BM25_WEIGHT = 0.3


class HybridSearchEngine:
    def __init__(self):
        self.vector_store = VectorStore()
        self.bm25 = BM25Retriever()
        self.embedder = GeminiEmbedder()

    async def search(
        self,
        query: str,
        department: Optional[str] = None,
        top_k: int = 5,
        expanded_queries: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        Run hybrid search and merge results.
        """
        # Use expanded queries if provided
        all_queries = [query]
        if expanded_queries:
            all_queries.extend(expanded_queries[:2])  # limit to 2 extra

        # -- Semantic search --
        query_embedding = await self.embedder.embed_query(query)
        semantic_results = self.vector_store.search(
            query_embedding=query_embedding,
            department=department,
            top_k=top_k * 2,
        )

        # -- BM25 search --
        bm25_results = self.bm25.search(query, department=department, top_k=top_k * 2)

        # -- Normalize BM25 scores to [0, 1] --
        if bm25_results:
            max_bm25 = max(r["bm25_score"] for r in bm25_results) or 1
            for r in bm25_results:
                r["normalized_bm25"] = r["bm25_score"] / max_bm25
        else:
            for r in bm25_results:
                r["normalized_bm25"] = 0.0

        # -- Build lookup maps --
        semantic_map = {r["chunk_id"]: r for r in semantic_results}
        bm25_map = {r["chunk_id"]: r for r in bm25_results}

        # -- Merge and score --
        all_chunk_ids = set(list(semantic_map.keys()) + list(bm25_map.keys()))
        merged = []
        for chunk_id in all_chunk_ids:
            sem = semantic_map.get(chunk_id)
            bm = bm25_map.get(chunk_id)

            sem_score = sem["semantic_score"] if sem else 0.0
            bm25_score = bm["normalized_bm25"] if bm else 0.0
            final_score = SEMANTIC_WEIGHT * sem_score + BM25_WEIGHT * bm25_score

            base = sem or bm
            merged.append({
                "chunk_id": chunk_id,
                "text": base["text"],
                "metadata": base["metadata"],
                "semantic_score": sem_score,
                "bm25_score": bm25_score,
                "final_score": final_score,
            })

        # -- Sort and return top_k --
        merged.sort(key=lambda x: x["final_score"], reverse=True)
        top_results = merged[:top_k]

        logger.info(
            f"Hybrid search: {len(semantic_results)} semantic + {len(bm25_results)} BM25 "
            f"→ {len(top_results)} merged results"
        )
        return top_results
