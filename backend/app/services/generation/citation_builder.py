"""
Citation Builder — assembles source citations from retrieved chunks.
"""
from typing import List
from app.models.chunk import Citation


class CitationBuilder:
    def build(self, chunks: List[dict]) -> List[Citation]:
        """
        Build citation objects from retrieved chunks.
        Deduplicates by document_id + page_number.
        """
        seen = set()
        citations = []

        for chunk in chunks:
            meta = chunk.get("metadata", {})
            doc_id = meta.get("document_id", "")
            page = meta.get("page_number")
            key = f"{doc_id}:{page}"

            if key in seen:
                continue
            seen.add(key)

            # Create a short excerpt (first 200 chars)
            excerpt = chunk.get("text", "")[:200].strip()
            if len(chunk.get("text", "")) > 200:
                excerpt += "..."

            citation = Citation(
                document_id=doc_id,
                document=meta.get("filename", "Unknown"),
                title=meta.get("document_title", "Unknown"),
                page=page if page and page > 0 else None,
                chunk_id=chunk.get("chunk_id", ""),
                excerpt=excerpt,
                relevance_score=round(chunk.get("final_score", chunk.get("semantic_score", 0.0)), 3),
            )
            citations.append(citation)

        # Sort by relevance
        citations.sort(key=lambda c: c.relevance_score, reverse=True)
        return citations
