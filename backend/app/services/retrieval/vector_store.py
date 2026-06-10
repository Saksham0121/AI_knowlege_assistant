"""
ChromaDB Vector Store — per-department collections.
Stores chunk text, embeddings, and metadata.
"""
import logging
from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings

logger = logging.getLogger(__name__)

# Singleton client
_chroma_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"✅ ChromaDB initialized at {settings.chroma_persist_dir}")
    return _chroma_client


def _collection_name(department: str) -> str:
    """Sanitize department name to valid ChromaDB collection name."""
    return f"dept_{department.lower().replace(' ', '_').replace('-', '_')}"


class VectorStore:
    def __init__(self):
        self.client = get_chroma_client()

    def _get_or_create_collection(self, department: str):
        name = _collection_name(department)
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},  # cosine similarity
        )

    def add_chunks(self, chunks: List[dict], embeddings: List[List[float]], department: str):
        """Store chunks with embeddings in the department's collection."""
        collection = self._get_or_create_collection(department)

        ids = [c["chunk_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "document_id": c["document_id"],
                "document_title": c["document_title"],
                "filename": c["filename"],
                "department": c["department"],
                "page_number": c.get("page_number") or 0,
                "chunk_index": c["chunk_index"],
            }
            for c in chunks
        ]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Stored {len(chunks)} chunks in collection {_collection_name(department)}")

    def search(
        self,
        query_embedding: List[float],
        department: Optional[str] = None,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[dict]:
        """
        Search for similar chunks.
        If department is specified, search only that collection.
        Otherwise, search all collections and merge results.
        """
        if department:
            collections_to_search = [department]
        else:
            # Search all department collections
            all_collections = self.client.list_collections()
            collections_to_search = [
                c.name.replace("dept_", "").replace("_", " ").title()
                for c in all_collections
                if c.name.startswith("dept_")
            ]

        results = []
        for dept in collections_to_search:
            try:
                collection = self._get_or_create_collection(dept)
                count = collection.count()
                if count == 0:
                    continue

                query_result = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, count),
                    where=where,
                    include=["documents", "metadatas", "distances"],
                )

                for i, doc_id in enumerate(query_result["ids"][0]):
                    distance = query_result["distances"][0][i]
                    # Convert cosine distance to similarity score
                    similarity = 1 - distance
                    results.append({
                        "chunk_id": doc_id,
                        "text": query_result["documents"][0][i],
                        "metadata": query_result["metadatas"][0][i],
                        "semantic_score": max(0.0, similarity),
                    })
            except Exception as e:
                logger.warning(f"Search error in dept {dept}: {e}")

        # Sort by semantic_score, return top_k
        results.sort(key=lambda x: x["semantic_score"], reverse=True)
        return results[:top_k]

    def delete_document(self, document_id: str):
        """Remove all chunks for a document from all collections."""
        all_collections = self.client.list_collections()
        for col_info in all_collections:
            try:
                collection = self.client.get_collection(col_info.name)
                collection.delete(where={"document_id": document_id})
            except Exception as e:
                logger.warning(f"Error deleting from {col_info.name}: {e}")

    def get_collection_stats(self) -> List[dict]:
        """Return stats for all department collections."""
        stats = []
        for col in self.client.list_collections():
            try:
                collection = self.client.get_collection(col.name)
                stats.append({"collection": col.name, "count": collection.count()})
            except Exception:
                pass
        return stats
