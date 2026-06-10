import uuid
import time
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import json

from app.core.dependencies import get_current_user
from app.core.database import get_database
from app.models.chat import ChatQuery, ChatResponse, ChatHistoryEntry

router = APIRouter()


@router.post("/query", response_model=ChatResponse)
async def query(
    payload: ChatQuery,
    current_user=Depends(get_current_user),
    db=Depends(get_database),
):
    from app.services.generation.rag_chain import RAGChain

    start_total = time.time()

    # Determine department filter
    dept_filter = payload.department
    if current_user["role"] in ("employee", "manager"):
        dept_filter = current_user["department"]

    rag = RAGChain()
    result = await rag.query(
        question=payload.question,
        department=dept_filter,
        user_id=str(current_user["_id"]),
    )

    query_id = str(uuid.uuid4())
    session_id = payload.session_id or str(uuid.uuid4())
    total_ms = (time.time() - start_total) * 1000

    # Store in history
    history_doc = {
        "user_id": str(current_user["_id"]),
        "session_id": session_id,
        "query_id": query_id,
        "question": payload.question,
        "answer": result["answer"],
        "confidence": result["confidence"],
        "citations": [c.dict() for c in result["citations"]],
        "department_filter": dept_filter,
        "feedback": None,
        "retrieval_time_ms": result.get("retrieval_time_ms"),
        "generation_time_ms": result.get("generation_time_ms"),
        "created_at": __import__("datetime").datetime.utcnow(),
    }
    await db.chat_history.insert_one(history_doc)

    # Store analytics event
    await db.query_events.insert_one({
        "user_id": str(current_user["_id"]),
        "department": current_user["department"],
        "query": payload.question,
        "success": result["confidence"] > 0.3,
        "confidence": result["confidence"],
        "retrieval_time_ms": result.get("retrieval_time_ms", 0),
        "generation_time_ms": result.get("generation_time_ms", 0),
        "document_ids_retrieved": result.get("document_ids", []),
        "timestamp": __import__("datetime").datetime.utcnow(),
    })

    return ChatResponse(
        answer=result["answer"],
        confidence=result["confidence"],
        citations=result["citations"],
        session_id=session_id,
        query_id=query_id,
        retrieval_time_ms=result.get("retrieval_time_ms"),
        generation_time_ms=result.get("generation_time_ms"),
    )


@router.get("/history")
async def get_history(
    session_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db=Depends(get_database),
):
    query_filter: dict = {"user_id": str(current_user["_id"])}
    if session_id:
        query_filter["session_id"] = session_id
    if search:
        query_filter["$or"] = [
            {"question": {"$regex": search, "$options": "i"}},
            {"answer": {"$regex": search, "$options": "i"}},
        ]

    total = await db.chat_history.count_documents(query_filter)
    skip = (page - 1) * page_size
    cursor = db.chat_history.find(query_filter).skip(skip).limit(page_size).sort("created_at", -1)

    history = []
    async for h in cursor:
        h["id"] = str(h["_id"])
        del h["_id"]
        history.append(h)

    return {"history": history, "total": total, "page": page, "page_size": page_size}


@router.delete("/history/{query_id}", status_code=204)
async def delete_chat(
    query_id: str,
    current_user=Depends(get_current_user),
    db=Depends(get_database),
):
    result = await db.chat_history.delete_one({
        "query_id": query_id,
        "user_id": str(current_user["_id"]),
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chat not found")


@router.get("/history/export")
async def export_chat_history(
    current_user=Depends(get_current_user),
    db=Depends(get_database),
):
    cursor = db.chat_history.find({"user_id": str(current_user["_id"])}).sort("created_at", 1)
    history = []
    async for h in cursor:
        h["id"] = str(h["_id"])
        del h["_id"]
        history.append(h)

    content = json.dumps(history, default=str, indent=2)
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=chat_history.json"},
    )
