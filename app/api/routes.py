from fastapi import APIRouter
from app.api import upload, chat

router = APIRouter()
router.include_router(upload.router, prefix="/upload", tags=["Upload"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])