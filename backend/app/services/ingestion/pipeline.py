"""
Full ingestion pipeline:
  1. Extract text from document
  2. Clean extracted text
  3. Chunk into overlapping segments
  4. Generate Gemini embeddings
  5. Store in ChromaDB
  6. Auto-generate summary/keywords with Gemini
  7. Update document status in MongoDB
"""
import logging
import time
from datetime import datetime
from app.services.ingestion.extractor import extract_text
from app.services.ingestion.cleaner import clean_text
from app.services.ingestion.chunker import ChunkingEngine
from app.services.embedding.gemini_embedder import GeminiEmbedder
from app.services.retrieval.vector_store import VectorStore
from app.services.generation.summarizer import DocumentSummarizer

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

        # Step 4: Embed
        embedder = GeminiEmbedder()
        texts = [c["text"] for c in chunks]
        embeddings = await embedder.embed_batch(texts)
        logger.info(f"  ✅ Generated {len(embeddings)} embeddings")

        # Step 5: Store in ChromaDB
        vector_store = VectorStore()
        vector_store.add_chunks(chunks, embeddings, department)
        logger.info(f"  ✅ Stored in ChromaDB collection: {department}")

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
