from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.core.database import get_database
from app.models.feedback import FeedbackCreate

router = APIRouter()


@router.post("/submit", status_code=201)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user=Depends(get_current_user),
    db=Depends(get_database),
):
    # Verify query_id exists
    chat = await db.chat_history.find_one({"query_id": payload.query_id})
    if not chat:
        raise HTTPException(status_code=404, detail="Query not found")

    # Update chat history with feedback
    await db.chat_history.update_one(
        {"query_id": payload.query_id},
        {"$set": {"feedback": payload.feedback}},
    )

    # Store dedicated feedback record
    await db.feedback.insert_one({
        "query_id": payload.query_id,
        "user_id": str(current_user["_id"]),
        "feedback": payload.feedback,
        "comment": payload.comment,
        "created_at": datetime.utcnow(),
    })

    return {"message": "Feedback submitted", "query_id": payload.query_id}
