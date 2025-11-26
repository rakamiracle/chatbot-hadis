from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from app.database.connection import get_db
from app.schemas.chat import ChatRequest, ChatResponse, Source
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import VectorSearch
from app.services.llm_service import LLMService
from app.models.chat_history import ChatHistory

# =====================
# 🔥 CODE BARU: logger
# =====================
from app.utils.logger import logger, log_query
# =====================
# 🔥 END CODE BARU
# =====================

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):

    # =====================
    # 🔥 CODE BARU: Start time logging
    # =====================
    start_time = datetime.utcnow()
    try:
        logger.info(f"Chat request: {request.query[:100]}")
    # =====================
    # 🔥 END CODE BARU
    # =====================

        embed = EmbeddingService()
        search = VectorSearch()
        llm = LLMService()
        
        qemb = await embed.generate_embedding(request.query)
        
        # Search dengan kitab_filter + document_ids
        chunks = await search.search_similar(
            qemb, 
            db,
            kitab_filter=request.kitab_filter,
            document_ids=request.document_ids
        )
        
        # =====================
        # 🔥 CODE BARU: warning jika tidak ada hasil
        # =====================
        if not chunks:
            logger.warning(f"No chunks found for query: {request.query}")
            raise HTTPException(
                404,
                "Tidak ditemukan hadis yang relevan dengan pertanyaan Anda. "
                "Silakan coba pertanyaan lain atau upload dokumen hadis yang lebih sesuai."
            )
        # =====================
        # 🔥 END CODE BARU
        # =====================

        answer = await llm.generate_response(request.query, chunks)
        
        # Buat list sumber
        sources = [
            Source(
                chunk_id=c['chunk_id'],
                text=c['text'][:200],
                page_number=c['page_number'],
                similarity_score=c['similarity'],
                kitab_name=c.get('kitab_name'),
                document_id=c['document_id']
            )
            for c in chunks
        ]
        
        # Session ID
        sid = request.session_id or str(uuid.uuid4())
        
        hist = ChatHistory(
            session_id=uuid.UUID(sid) if request.session_id else uuid.uuid4(),
            user_query=request.query,
            bot_response=answer,
            sources=[]
        )
        db.add(hist)
        await db.commit()

        # =====================
        # 🔥 CODE BARU: Log query performance
        # =====================
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_query(sid, request.query, response_time)
        logger.info(f"Chat response generated in {response_time:.0f}ms")
        # =====================
        # 🔥 END CODE BARU
        # =====================

        return ChatResponse(answer=answer, sources=sources, session_id=sid)
    
    # =====================
    # 🔥 CODE BARU: Error handling
    # =====================
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Terjadi kesalahan saat memproses pertanyaan: {str(e)}")
    # =====================
    # 🔥 END CODE BARU
    # =====================
