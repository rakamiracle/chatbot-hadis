from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.schemas.chat import ChatRequest, ChatResponse, Source
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import VectorSearch
from app.services.llm_service import LLMService
from app.services.query_cache import query_cache
from app.models.chat_history import ChatHistory
from app.utils.logger import logger, log_query
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Chat request: {request.query[:100]}")
        
        embed = EmbeddingService()
        search = VectorSearch()
        llm = LLMService()
        
        # Check cache untuk embedding
        qemb = query_cache.get_embedding(request.query)
        if qemb:
            logger.info("Using cached embedding")
        else:
            qemb = await embed.generate_embedding(request.query)
            query_cache.set_embedding(request.query, qemb)
        
        # Check cache untuk results
        cache_key_filters = {
            'kitab': request.kitab_filter,
            'docs': request.document_ids
        }
        
        chunks = query_cache.get_results(request.query, cache_key_filters)
        if chunks:
            logger.info("Using cached search results")
        else:
            # Search dengan hybrid method
            chunks = await search.search_similar(
                qemb,
                request.query,  # Pass raw query text
                db,
                kitab_filter=request.kitab_filter,
                document_ids=request.document_ids
            )
            query_cache.set_results(request.query, chunks, cache_key_filters)
        
        if not chunks:
            logger.warning(f"No chunks found for query: {request.query}")
            raise HTTPException(404, "Tidak ditemukan hadis yang relevan. Coba pertanyaan lain atau upload dokumen yang lebih sesuai.")
        
        # Generate response
        answer = await llm.generate_response(request.query, chunks)
        
        sources = [
            Source(
                chunk_id=c['chunk_id'],
                text=c['text'][:200],
                page_number=c['page_number'],
                similarity_score=c.get('final_score', c['similarity']),
                kitab_name=c.get('kitab_name'),
                document_id=c['document_id']
            )
            for c in chunks
        ]
        
        sid = request.session_id or str(uuid.uuid4())
        hist = ChatHistory(
            session_id=uuid.UUID(sid) if request.session_id else uuid.uuid4(),
            user_query=request.query,
            bot_response=answer,
            sources=[]
        )
        db.add(hist)
        await db.commit()
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_query(sid, request.query, response_time)
        logger.info(f"Chat response in {response_time:.0f}ms")
        
        return ChatResponse(answer=answer, sources=sources, session_id=sid)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Error: {str(e)}")

@router.post("/clear-cache")
async def clear_cache():
    """Clear query cache"""
    query_cache.clear()
    return {"message": "Cache cleared"}