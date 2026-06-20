"""
PDF document loading and chunking.

Loads PDF files from a directory, extracts text page-by-page,
and splits into chunks suitable for the RAG pipeline.
"""

import logging
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


def load_pdf(pdf_path: str | Path) -> List[Document]:
    """Load a single PDF file and return one Document per page.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of Document objects, one per page.

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        ValueError: If the file is not a PDF.
    """
    from pypdf import PdfReader

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {pdf_path}")

    logger.info("Loading PDF: %s", pdf_path.name)

    reader = PdfReader(str(pdf_path))
    documents = []

    for page_num, page in enumerate(reader.pages, 1):
        text = page.extract_text()
        if text and text.strip():
            doc = Document(
                page_content=text,
                metadata={
                    "source": pdf_path.name,
                    "page": page_num,
                    "chunk_id": f"{pdf_path.stem}_p{page_num}",
                },
            )
            documents.append(doc)

    logger.info("Loaded %d pages from %s", len(documents), pdf_path.name)
    return documents


def load_pdfs_from_directory(directory: str | Path) -> List[Document]:
    """Load all PDF files from a directory.

    Args:
        directory: Path to directory containing PDF files.

    Returns:
        List of Document objects from all PDFs.

    Raises:
        FileNotFoundError: If the directory doesn't exist.
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")
    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {dir_path}")

    pdf_files = sorted(dir_path.glob("*.pdf"))

    if not pdf_files:
        logger.warning("No PDF files found in: %s", dir_path)
        return []

    logger.info("Found %d PDF files in %s", len(pdf_files), dir_path)

    all_documents = []
    for pdf_file in pdf_files:
        try:
            docs = load_pdf(pdf_file)
            all_documents.extend(docs)
        except Exception as e:
            logger.error("Failed to load %s: %s", pdf_file.name, e)

    logger.info("Total pages loaded: %d", len(all_documents))
    return all_documents


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """Split documents into smaller chunks for better retrieval.

    Args:
        documents: List of Document objects (e.g., one per PDF page).
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Number of overlapping characters between chunks.

    Returns:
        List of chunked Document objects with updated metadata.
    """
    if not documents:
        return []

    logger.info(
        "Chunking %d documents (chunk_size=%d, overlap=%d)",
        len(documents),
        chunk_size,
        chunk_overlap,
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(documents)

    # Update chunk_id metadata for each chunk
    for i, chunk in enumerate(chunks):
        source = chunk.metadata.get("source", "unknown")
        page = chunk.metadata.get("page", 0)
        chunk.metadata["chunk_id"] = f"{Path(source).stem}_p{page}_c{i}"

    logger.info("Created %d chunks from %d documents", len(chunks), len(documents))
    return chunks


def load_and_chunk_pdfs(
    path: str | Path,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """Load PDFs and chunk them in one step.

    Accepts either a single PDF file or a directory of PDFs.

    Args:
        path: Path to a PDF file or directory of PDFs.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Overlap between chunks.

    Returns:
        List of chunked Document objects ready for ingestion.
    """
    path = Path(path)

    if path.is_file():
        documents = load_pdf(path)
    elif path.is_dir():
        documents = load_pdfs_from_directory(path)
    else:
        raise FileNotFoundError(f"Path not found: {path}")

    chunks = chunk_documents(documents, chunk_size, chunk_overlap)
    return chunks
