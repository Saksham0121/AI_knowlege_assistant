"""
Full ingestion pipeline:
  1. Extract text from document
  2. Clean extracted text
  3. Chunk into overlapping segments
  4. Convert to LangChain Documents
  5. Ingest via new RAGAgent
  6. Auto-generate summary/keywords with Gemini
  7. Update document status in MongoDB
"""
import logging
import time
import asyncio
from datetime import datetime
from app.services.ingestion.extractor import extract_text
from app.services.ingestion.cleaner import clean_text
from app.services.ingestion.chunker import ChunkingEngine
from app.services.rag_agent.summarizer import DocumentSummarizer
from app.services.rag_agent.agent import RAGAgent
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


async def run_ingestion_pipeline(
    document_id: str,
    file_path: str,
    file_ext: str,
    department: str,
    title: str,
    filename: str,
    db,
):
    """
    Full async ingestion pipeline. Called as a background task.
    """
    start = time.time()
    logger.info(f"🔄 Starting ingestion pipeline for doc {document_id}")

    try:
        # Step 1: Extract text
        pages = extract_text(file_path, file_ext)
        logger.info(f"  ✅ Extracted {len(pages)} pages")

        # Step 2: Clean text
        cleaned_pages = [(page_num, clean_text(text)) for page_num, text in pages]
        cleaned_pages = [(p, t) for p, t in cleaned_pages if t.strip()]

        # Step 3: Chunk
        chunker = ChunkingEngine()
        chunks = chunker.chunk_pages(cleaned_pages, document_id, title, filename, department)
        logger.info(f"  ✅ Created {len(chunks)} chunks")

        if not chunks:
            raise ValueError("No text content extracted from document")

        # Step 4: Convert to LangChain Documents
        lc_docs = []
        for c in chunks:
            lc_docs.append(Document(
                page_content=c["text"],
                metadata={
                    "source": filename,
                    "page": c.get("page", 0),
                    "chunk_id": c.get("chunk_id", ""),
                    "department": department,
                }
            ))

        # Step 5: Ingest via RAGAgent
        agent = RAGAgent()
        await asyncio.to_thread(agent.ingest, lc_docs)
        logger.info(f"  ✅ Ingested into FAISS via RAGAgent")

        # Step 6: Auto-summarize
        full_text = "\n\n".join(t for _, t in cleaned_pages[:10])  # first 10 pages
        summarizer = DocumentSummarizer()
        meta = await summarizer.summarize(full_text, title)
        logger.info(f"  ✅ Generated summary & keywords")

        # Step 7: Update MongoDB document record
        elapsed = time.time() - start
        await db.documents.update_one(
            {"document_id": document_id},
            {"$set": {
                "status": "processed",
                "total_chunks": len(chunks),
                "summary": meta.get("summary"),
                "keywords": meta.get("keywords", []),
                "topics": meta.get("topics", []),
                "auto_department": meta.get("department"),
                "processing_time_seconds": round(elapsed, 2),
                "processed_at": datetime.utcnow(),
            }},
        )
        logger.info(f"✅ Ingestion complete for {document_id} in {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"❌ Ingestion failed for {document_id}: {e}", exc_info=True)
        await db.documents.update_one(
            {"document_id": document_id},
            {"$set": {"status": "failed", "error": str(e)}},
        )
