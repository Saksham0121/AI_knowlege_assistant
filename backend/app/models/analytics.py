from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class QueryEvent(BaseModel):
    """Stored for every chat query — powers analytics."""
    user_id: str
    department: str
    query: str
    success: bool
    confidence: float
    retrieval_time_ms: float
    generation_time_ms: float
    document_ids_retrieved: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DashboardStats(BaseModel):
    total_users: int
    total_documents: int
    total_queries: int
    avg_confidence: float
    success_rate: float
    avg_retrieval_time_ms: float
    avg_generation_time_ms: float


class DepartmentStat(BaseModel):
    department: str
    query_count: int
    document_count: int
    active_users: int


class TopDocument(BaseModel):
    document_id: str
    title: str
    filename: str
    department: str
    reference_count: int


class QueryTrend(BaseModel):
    date: str  # YYYY-MM-DD
    count: int


class AnalyticsDashboard(BaseModel):
    stats: DashboardStats
    department_stats: List[DepartmentStat]
    top_documents: List[TopDocument]
    query_trend: List[QueryTrend]
    failed_query_count: int
    positive_feedback_rate: float
