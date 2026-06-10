from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from app.core.dependencies import get_current_user, require_manager_or_admin
from app.core.database import get_database

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    current_user=Depends(require_manager_or_admin),
    db=Depends(get_database),
):
    # Build dept filter for managers
    dept_filter = {}
    if current_user["role"] == "manager":
        dept_filter = {"department": current_user["department"]}

    total_users = await db.users.count_documents({})
    total_documents = await db.documents.count_documents(dept_filter if dept_filter else {})
    total_queries = await db.query_events.count_documents(dept_filter if dept_filter else {})

    # Avg confidence
    pipeline_conf = [
        {"$match": dept_filter} if dept_filter else {"$match": {}},
        {"$group": {"_id": None, "avg": {"$avg": "$confidence"}, "success_count": {"$sum": {"$cond": ["$success", 1, 0]}}}},
    ]
    conf_result = await db.query_events.aggregate(pipeline_conf).to_list(1)
    avg_confidence = round((conf_result[0]["avg"] if conf_result else 0) * 100, 1)
    success_rate = round(
        (conf_result[0]["success_count"] / total_queries * 100) if total_queries > 0 else 0, 1
    )

    # Retrieval / generation time
    pipeline_time = [
        {"$match": dept_filter} if dept_filter else {"$match": {}},
        {"$group": {"_id": None, "avg_r": {"$avg": "$retrieval_time_ms"}, "avg_g": {"$avg": "$generation_time_ms"}}},
    ]
    time_result = await db.query_events.aggregate(pipeline_time).to_list(1)
    avg_retrieval = round(time_result[0]["avg_r"] if time_result else 0, 1)
    avg_generation = round(time_result[0]["avg_g"] if time_result else 0, 1)

    # Department breakdown
    dept_pipeline = [
        {"$group": {"_id": "$department", "query_count": {"$sum": 1}}},
        {"$sort": {"query_count": -1}},
    ]
    dept_stats_raw = await db.query_events.aggregate(dept_pipeline).to_list(20)
    dept_stats = [{"department": d["_id"], "query_count": d["query_count"]} for d in dept_stats_raw]

    # Top documents by citation
    top_docs_pipeline = [
        {"$unwind": "$citations"},
        {"$group": {"_id": "$citations.document_id", "count": {"$sum": 1}, "title": {"$first": "$citations.title"}, "filename": {"$first": "$citations.document"}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    top_docs_raw = await db.chat_history.aggregate(top_docs_pipeline).to_list(10)
    top_documents = [
        {"document_id": d["_id"], "title": d.get("title", ""), "filename": d.get("filename", ""), "reference_count": d["count"]}
        for d in top_docs_raw
    ]

    # 30-day query trend
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    trend_pipeline = [
        {"$match": {"timestamp": {"$gte": thirty_days_ago}}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    trend_raw = await db.query_events.aggregate(trend_pipeline).to_list(30)
    query_trend = [{"date": t["_id"], "count": t["count"]} for t in trend_raw]

    # Feedback rate
    total_feedback = await db.feedback.count_documents({})
    positive_feedback = await db.feedback.count_documents({"feedback": "positive"})
    feedback_rate = round((positive_feedback / total_feedback * 100) if total_feedback > 0 else 0, 1)

    return {
        "stats": {
            "total_users": total_users,
            "total_documents": total_documents,
            "total_queries": total_queries,
            "avg_confidence": avg_confidence,
            "success_rate": success_rate,
            "avg_retrieval_time_ms": avg_retrieval,
            "avg_generation_time_ms": avg_generation,
        },
        "department_stats": dept_stats,
        "top_documents": top_documents,
        "query_trend": query_trend,
        "positive_feedback_rate": feedback_rate,
    }


@router.get("/queries")
async def get_recent_queries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20),
    current_user=Depends(require_manager_or_admin),
    db=Depends(get_database),
):
    query_filter = {}
    if current_user["role"] == "manager":
        query_filter["department"] = current_user["department"]

    total = await db.query_events.count_documents(query_filter)
    skip = (page - 1) * page_size
    cursor = db.query_events.find(query_filter).skip(skip).limit(page_size).sort("timestamp", -1)
    events = []
    async for e in cursor:
        e["id"] = str(e["_id"])
        del e["_id"]
        events.append(e)

    return {"queries": events, "total": total}
