from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.chunk import Citation


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    citations: Optional[List[Citation]] = []
    confidence: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatQuery(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    department: Optional[str] = None  # filter retrieval to dept
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    citations: List[Citation]
    session_id: str
    query_id: str
    retrieval_time_ms: Optional[float] = None
    generation_time_ms: Optional[float] = None


class ChatHistoryEntry(BaseModel):
    id: Optional[str] = None
    user_id: str
    session_id: str
    question: str
    answer: str
    confidence: float
    citations: List[Citation]
    department_filter: Optional[str] = None
    feedback: Optional[str] = None  # "positive" | "negative"
    retrieval_time_ms: Optional[float] = None
    generation_time_ms: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
