"""
RAG Chain — the core generation engine.
Orchestrates: query expansion → hybrid search → reranking → Gemini generation → citation assembly
"""
import time
import logging
import asyncio
from typing import Optional, List, Dict, Any
import google.generativeai as genai

from app.core.config import settings
from app.services.retrieval.hybrid_search import HybridSearchEngine
from app.services.retrieval.query_expander import QueryExpander
from app.services.retrieval.reranker import GeminiReranker
from app.services.generation.citation_builder import CitationBuilder
from app.models.chunk import Citation

logger = logging.getLogger(__name__)

RAG_PROMPT_TEMPLATE = """You are InsightFlow AI, an intelligent enterprise knowledge assistant.

Your role: Answer questions ONLY based on the provided context from the organization's knowledge base.

STRICT RULES:
1. Answer ONLY from the provided context. Do NOT use external knowledge.
2. If the answer cannot be found in the context, say exactly: "I could not find relevant information about this in the knowledge base."
3. Be precise, professional, and concise.
4. When referencing specific information, mention the source document naturally (e.g., "According to [document name]...").
5. Structure longer answers with clear bullet points or numbered lists when appropriate.

CONTEXT FROM KNOWLEDGE BASE:
{context}

QUESTION: {question}

ANSWER:"""

TOP_K = 5


class RAGChain:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.hybrid_search = HybridSearchEngine()
        self.query_expander = QueryExpander()
        self.reranker = GeminiReranker()
        self.citation_builder = CitationBuilder()

    async def query(
        self,
        question: str,
        department: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full RAG pipeline:
        1. Expand query
        2. Hybrid search
        3. Rerank
        4. Generate with Gemini
        5. Build citations
        6. Calculate confidence
        """
        # Step 1: Query expansion
        t0 = time.time()
        expanded_queries = await self.query_expander.expand(question)

        # Step 2: Hybrid retrieval
        t_retrieval_start = time.time()
        retrieved_chunks = await self.hybrid_search.search(
            query=question,
            department=department,
            top_k=TOP_K * 2,
            expanded_queries=expanded_queries[1:],
        )
        retrieval_time_ms = (time.time() - t_retrieval_start) * 1000

        # Step 3: Rerank
        reranked_chunks = await self.reranker.rerank(question, retrieved_chunks)
        top_chunks = reranked_chunks[:TOP_K]

        if not top_chunks:
            return {
                "answer": "I could not find relevant information about this in the knowledge base. Please ensure relevant documents have been uploaded.",
                "confidence": 0.0,
                "citations": [],
                "retrieval_time_ms": retrieval_time_ms,
                "generation_time_ms": 0.0,
                "document_ids": [],
            }

        # Step 4: Build context string
        context_parts = []
        for i, chunk in enumerate(top_chunks, 1):
            meta = chunk.get("metadata", {})
            context_parts.append(
                f"[Source {i}: {meta.get('document_title', 'Unknown')} - Page {meta.get('page_number', 'N/A')}]\n{chunk['text']}"
            )
        context = "\n\n---\n\n".join(context_parts)

        # Step 5: Generate answer
        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
        t_gen_start = time.time()

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1024,
                ),
            )
            answer = response.text.strip()
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            answer = "I encountered an error generating the answer. Please try again."

        generation_time_ms = (time.time() - t_gen_start) * 1000

        # Step 6: Citations
        citations = self.citation_builder.build(top_chunks)

        # Step 7: Confidence score
        confidence = self._calculate_confidence(top_chunks, answer)

        document_ids = list({c.get("metadata", {}).get("document_id", "") for c in top_chunks})

        logger.info(
            f"RAG complete | confidence={confidence:.2f} | "
            f"retrieval={retrieval_time_ms:.0f}ms | generation={generation_time_ms:.0f}ms"
        )

        return {
            "answer": answer,
            "confidence": confidence,
            "citations": citations,
            "retrieval_time_ms": retrieval_time_ms,
            "generation_time_ms": generation_time_ms,
            "document_ids": document_ids,
        }

    def _calculate_confidence(self, chunks: List[dict], answer: str) -> float:
        """
        Heuristic confidence score based on:
        - Average semantic score of top chunks
        - Whether the answer is a "not found" response
        """
        if "could not find" in answer.lower() or not chunks:
            return 0.1

        avg_semantic = sum(c.get("semantic_score", 0) for c in chunks) / len(chunks)
        avg_final = sum(c.get("final_score", c.get("semantic_score", 0)) for c in chunks) / len(chunks)

        # Weight final score more
        raw_confidence = 0.4 * avg_semantic + 0.6 * avg_final

        # Cap and scale to 0-1
        confidence = min(max(raw_confidence, 0.0), 1.0)
        return round(confidence, 3)
