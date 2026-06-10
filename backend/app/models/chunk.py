from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    filename: str
    department: str
    page_number: Optional[int] = None
    chunk_index: int
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Citation(BaseModel):
    document_id: str
    document: str   # filename
    title: str
    page: Optional[int] = None
    chunk_id: str
    excerpt: str    # short text preview
    relevance_score: float = 0.0
