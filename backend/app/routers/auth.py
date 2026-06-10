from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import get_database
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, verify_token
from app.models.user import UserCreate, LoginRequest, TokenResponse, UserResponse, RefreshRequest

router = APIRouter()


def _serialize_user(user: dict) -> UserResponse:
    user["id"] = str(user["_id"])
    return UserResponse(**{k: v for k, v in user.items() if k != "_id"})


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db=Depends(get_database)):
    # Check duplicate email
    existing = await db.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # First user → auto admin
    user_count = await db.users.count_documents({})
    role = "admin" if user_count == 0 else payload.role

    user_doc = {
        "name": payload.name,
        "email": payload.email,
        "role": role,
        "department": payload.department,
        "is_active": True,
        "hashed_password": hash_password(payload.password),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_login": None,
    }
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    user_id = str(result.inserted_id)
    token_data = {"sub": user_id, "role": role, "department": user_doc["department"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_serialize_user(user_doc),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db=Depends(get_database)):
    user = await db.users.find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is disabled")

    # Update last_login
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.utcnow()}})
    user["last_login"] = datetime.utcnow()

    user_id = str(user["_id"])
    token_data = {"sub": user_id, "role": user["role"], "department": user["department"]}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_serialize_user(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(payload: RefreshRequest, db=Depends(get_database)):
    token_data = verify_token(payload.refresh_token)
    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    from bson import ObjectId
    user = await db.users.find_one({"_id": ObjectId(token_data["sub"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = str(user["_id"])
    new_token_data = {"sub": user_id, "role": user["role"], "department": user["department"]}
    new_access = create_access_token(new_token_data)
    new_refresh = create_refresh_token(new_token_data)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=_serialize_user(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(db=Depends(get_database), credentials=Depends(__import__("fastapi").security.HTTPBearer())):
    from app.core.dependencies import get_current_user
    # re-route through dependency — kept simple here
    from fastapi import Request
    raise HTTPException(status_code=501, detail="Use /me via dependency injection")
