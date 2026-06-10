from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from app.core.dependencies import require_admin, get_current_user
from app.core.database import get_database
from app.models.user import UserUpdate, UserResponse

router = APIRouter()


def _serialize_user(user: dict) -> dict:
    user["id"] = str(user["_id"])
    del user["_id"]
    del user["hashed_password"]
    return user


@router.get("/users")
async def list_users(
    role: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20),
    current_user=Depends(require_admin),
    db=Depends(get_database),
):
    query_filter: dict = {}
    if role:
        query_filter["role"] = role
    if department:
        query_filter["department"] = department

    total = await db.users.count_documents(query_filter)
    skip = (page - 1) * page_size
    cursor = db.users.find(query_filter, {"hashed_password": 0}).skip(skip).limit(page_size)
    users = []
    async for u in cursor:
        u["id"] = str(u["_id"])
        del u["_id"]
        users.append(u)

    return {"users": users, "total": total}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user=Depends(require_admin),
    db=Depends(get_database),
):
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="Nothing to update")

    update_data["updated_at"] = datetime.utcnow()
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    updated = await db.users.find_one({"_id": ObjectId(user_id)}, {"hashed_password": 0})
    updated["id"] = str(updated["_id"])
    del updated["_id"]
    return updated


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    current_user=Depends(require_admin),
    db=Depends(get_database),
):
    result = await db.users.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/settings")
async def get_settings(current_user=Depends(require_admin)):
    from app.core.config import settings as s
    return {
        "mongodb_db_name": s.mongodb_db_name,
        "chroma_persist_dir": s.chroma_persist_dir,
        "storage_dir": s.storage_dir,
        "app_env": s.app_env,
        "rate_limit_per_minute": s.rate_limit_per_minute,
        "jwt_access_token_expire_minutes": s.jwt_access_token_expire_minutes,
    }
