from fastapi import APIRouter
from app.api import chat, upload, documents, analytics

router = APIRouter()

router.include_router(chat.router, prefix="/chat", tags=["chat"])
router.include_router(upload.router, prefix="/upload", tags=["upload"])
router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])