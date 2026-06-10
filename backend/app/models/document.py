from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


DocumentStatus = Literal["uploading", "processing", "processed", "failed"]


class DocumentBase(BaseModel):
    title: str
    department: str = "General"


class DocumentCreate(DocumentBase):
    pass


class DocumentMetadata(BaseModel):
    document_id: str
    title: str
    filename: str
    file_type: str  # pdf, docx, pptx, txt
    file_size: int  # bytes
    department: str
    uploaded_by: str  # user_id
    uploaded_by_name: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    status: DocumentStatus = "uploading"
    total_chunks: int = 0
    summary: Optional[str] = None
    keywords: List[str] = []
    topics: List[str] = []
    auto_department: Optional[str] = None  # AI-classified department
    storage_path: str = ""


class DocumentResponse(DocumentMetadata):
    id: str

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int
