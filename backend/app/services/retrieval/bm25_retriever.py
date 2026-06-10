"""
BM25 keyword retrieval — in-memory index built per query from ChromaDB documents.
"""
import logging
from typing import List, Optional
from rank_bm25 import BM25Okapi
from app.services.retrieval.vector_store import VectorStore

logger = logging.getLogger(__name__)


class BM25Retriever:
    def __init__(self):
        self.vector_store = VectorStore()

    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace + lowercase tokenizer."""
        return text.lower().split()

    def search(
        self,
        query: str,
        department: Optional[str] = None,
        top_k: int = 10,
    ) -> List[dict]:
        """
        Retrieve top_k chunks using BM25 keyword search.
        Builds an in-memory BM25 index from the ChromaDB collection.
        """
        try:
            # Get all chunks from the relevant collection(s)
            chroma_client = self.vector_store.client

            if department:
                col_name = f"dept_{department.lower().replace(' ', '_').replace('-', '_')}"
                try:
                    collection = chroma_client.get_collection(col_name)
                    all_docs = collection.get(include=["documents", "metadatas"])
                except Exception:
                    return []
            else:
                # Merge across all department collections
                all_docs = {"ids": [], "documents": [], "metadatas": []}
                for col in chroma_client.list_collections():
                    if not col.name.startswith("dept_"):
                        continue
                    try:
                        c = chroma_client.get_collection(col.name)
                        result = c.get(include=["documents", "metadatas"])
                        all_docs["ids"].extend(result["ids"])
                        all_docs["documents"].extend(result["documents"])
                        all_docs["metadatas"].extend(result["metadatas"])
                    except Exception:
                        continue

            if not all_docs["documents"]:
                return []

            # Build BM25 index
            tokenized_corpus = [self._tokenize(doc) for doc in all_docs["documents"]]
            bm25 = BM25Okapi(tokenized_corpus)

            # Score query
            tokenized_query = self._tokenize(query)
            scores = bm25.get_scores(tokenized_query)

            # Build result list
            results = []
            for i, score in enumerate(scores):
                if score > 0:
                    results.append({
                        "chunk_id": all_docs["ids"][i],
                        "text": all_docs["documents"][i],
                        "metadata": all_docs["metadatas"][i],
                        "bm25_score": float(score),
                    })

            # Sort by score and return top_k
            results.sort(key=lambda x: x["bm25_score"], reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"BM25 search error: {e}")
            return []
