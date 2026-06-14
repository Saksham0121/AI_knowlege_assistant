import os
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import FileResponse
from bson import ObjectId

from app.core.dependencies import get_current_user, require_manager_or_admin
from app.core.database import get_database
from app.models.document import DocumentResponse, DocumentListResponse
from app.services.ingestion.pipeline import run_ingestion_pipeline
from app.core.config import settings
from app.core.security import verify_token

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


# (Keep all intermediate routes unchanged, replacing from download_document route onward)
@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    db=Depends(get_database),
):
    # Try to get token from header first, then query param
    auth_header = request.headers.get("Authorization")
    actual_token = None
    if auth_header and auth_header.startswith("Bearer "):
        actual_token = auth_header.split(" ")[1]
    elif token:
        actual_token = token

    if not actual_token:
        raise HTTPException(status_code=401, detail="Authentication credentials missing")

    # Validate token
    payload = verify_token(actual_token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Retrieve document
    doc = await db.documents.find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Enforce department permissions for employee/manager
    if user.get("role") in ["employee", "manager"] and doc.get("department") != user.get("department"):
        raise HTTPException(status_code=403, detail="Access denied to this department's documents")

    path = doc.get("storage_path", "")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(path, filename=doc["filename"])



@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    department: str = Form("General"),
    title: Optional[str] = Form(None),
    current_user=Depends(require_manager_or_admin),
    db=Depends(get_database),
):
    # Validate extension
    filename = file.filename or "document"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Read and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 100 MB")

    doc_id = str(uuid.uuid4())
    doc_title = title or os.path.splitext(filename)[0]

    # Save raw file
    raw_path = os.path.join(settings.storage_dir, "raw_documents", f"{doc_id}_{filename}")
    with open(raw_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc_meta = {
        "document_id": doc_id,
        "title": doc_title,
        "filename": filename,
        "file_type": ext.lstrip("."),
        "file_size": len(content),
        "department": department,
        "uploaded_by": str(current_user["_id"]),
        "uploaded_by_name": current_user["name"],
        "upload_date": datetime.utcnow(),
        "status": "processing",
        "total_chunks": 0,
        "summary": None,
        "keywords": [],
        "topics": [],
        "storage_path": raw_path,
    }
    result = await db.documents.insert_one(doc_meta)
    doc_meta["id"] = str(result.inserted_id)

    # Run pipeline in background
    background_tasks.add_task(run_ingestion_pipeline, doc_id, raw_path, ext, department, doc_title, filename, db)

    return DocumentResponse(**doc_meta)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db=Depends(get_database),
):
    query: dict = {}

    # Employees/managers only see their department if not admin
    if current_user["role"] == "employee":
        query["department"] = current_user["department"]
    elif current_user["role"] == "manager":
        query["department"] = current_user["department"]
    elif department:
        query["department"] = department

    if status:
        query["status"] = status

    total = await db.documents.count_documents(query)
    skip = (page - 1) * page_size
    cursor = db.documents.find(query).skip(skip).limit(page_size).sort("upload_date", -1)
    docs = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        docs.append(DocumentResponse(**{k: v for k, v in doc.items() if k != "_id"}))

    return DocumentListResponse(documents=docs, total=total, page=page, page_size=page_size)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user=Depends(get_current_user),
    db=Depends(get_database),
):
    doc = await db.documents.find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc["id"] = str(doc["_id"])
    return DocumentResponse(**{k: v for k, v in doc.items() if k != "_id"})


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    current_user=Depends(require_manager_or_admin),
    db=Depends(get_database),
):
    doc = await db.documents.find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from vector store
    try:
        from app.services.retrieval.vector_store import VectorStore
        vs = VectorStore()
        vs.delete_document(document_id)
    except Exception:
        pass

    # Remove file
    try:
        if os.path.exists(doc.get("storage_path", "")):
            os.remove(doc["storage_path"])
    except Exception:
        pass

    await db.documents.delete_one({"document_id": document_id})



