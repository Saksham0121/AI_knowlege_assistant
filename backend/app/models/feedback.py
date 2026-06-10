from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

FeedbackType = Literal["positive", "negative"]


class FeedbackCreate(BaseModel):
    query_id: str
    feedback: FeedbackType
    comment: str = ""


class FeedbackInDB(FeedbackCreate):
    id: Optional[str] = None
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


from typing import Optional
