"""
Intelligent chunking engine using Recursive Character Text Splitter.
chunk_size=700, chunk_overlap=100
"""
import uuid
from typing import List, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)

CHUNK_SIZE = 700
CHUNK_OVERLAP = 100


class ChunkingEngine:
    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

    def chunk_pages(
        self,
        pages: List[Tuple[int, str]],  # (page_number, cleaned_text)
        document_id: str,
        document_title: str,
        filename: str,
        department: str,
    ) -> List[dict]:
        """
        Split pages into overlapping chunks.
        Returns list of chunk dicts with metadata.
        """
        all_chunks = []
        global_chunk_index = 0

        for page_num, page_text in pages:
            if not page_text.strip():
                continue

            splits = self.splitter.split_text(page_text)

            for split_text in splits:
                if not split_text.strip():
                    continue

                chunk = {
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "document_title": document_title,
                    "filename": filename,
                    "department": department,
                    "page_number": page_num,
                    "chunk_index": global_chunk_index,
                    "text": split_text.strip(),
                    "char_count": len(split_text),
                }
                all_chunks.append(chunk)
                global_chunk_index += 1

        logger.info(f"Chunked document {document_id}: {len(all_chunks)} chunks from {len(pages)} pages")
        return all_chunks
