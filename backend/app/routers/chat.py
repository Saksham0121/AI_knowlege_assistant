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
    from app.services.rag_agent.agent import RAGAgent
    import asyncio

    start_total = time.time()

    # Determine department filter
    dept_filter = payload.department
    if current_user["role"] in ("employee", "manager"):
        dept_filter = current_user["department"]

    agent = RAGAgent()
    result = await asyncio.to_thread(
        agent.smart_query,
        payload.question,
        dept_filter,
    )

    query_id = str(uuid.uuid4())
    session_id = payload.session_id or str(uuid.uuid4())
    total_ms = (time.time() - start_total) * 1000

    # Build citations mapping
    from app.models.chunk import Citation
    citations = []
    for s in result.get("sources", []):
        citations.append(Citation(
            document_id=s.get("source", ""),
            document_title=s.get("source", ""),
            page_number=s.get("page", 0) if isinstance(s.get("page"), int) else 0,
            chunk_id=s.get("chunk_id", ""),
            text=s.get("content_preview", ""),
            semantic_score=s.get("relevance_score", 0.0),
            final_score=s.get("relevance_score", 0.0),
        ))

    confidence = 0.9 if result.get("source_type") == "rag" and len(citations) > 0 else 0.5

    # Store in history
    history_doc = {
        "user_id": str(current_user["_id"]),
        "session_id": session_id,
        "query_id": query_id,
        "question": payload.question,
        "answer": result["answer"],
        "confidence": confidence,
        "citations": [c.dict() for c in citations],
        "department_filter": dept_filter,
        "feedback": None,
        "retrieval_time_ms": total_ms,
        "generation_time_ms": total_ms,
        "created_at": __import__("datetime").datetime.utcnow(),
    }
    await db.chat_history.insert_one(history_doc)

    # Store analytics event
    await db.query_events.insert_one({
        "user_id": str(current_user["_id"]),
        "department": current_user["department"],
        "query": payload.question,
        "success": confidence > 0.3,
        "confidence": confidence,
        "retrieval_time_ms": total_ms,
        "generation_time_ms": total_ms,
        "document_ids_retrieved": [c.document_id for c in citations],
        "timestamp": __import__("datetime").datetime.utcnow(),
    })

    return ChatResponse(
        answer=result["answer"],
        confidence=confidence,
        citations=citations,
        session_id=session_id,
        query_id=query_id,
        retrieval_time_ms=total_ms,
        generation_time_ms=total_ms,
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
