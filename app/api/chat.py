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
import asyncio

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"Query: {request.query[:100]}")
        
        # Initialize services
        embed_service = EmbeddingService()
        search_service = VectorSearch()
        llm_service = LLMService()
        
        # OPTIMIZATION 1: Check full cache first
        cache_key_filters = {
            'kitab': request.kitab_filter,
            'docs': request.document_ids
        }
        
        cached_chunks = query_cache.get_results(request.query, cache_key_filters)
        
        if cached_chunks:
            logger.info("✓ Full cache hit")
            chunks = cached_chunks
        else:
            # OPTIMIZATION 2: Check embedding cache
            qemb = query_cache.get_embedding(request.query)
            
            if qemb:
                logger.info("✓ Embedding cache hit")
            else:
                logger.info("Generating embedding...")
                qemb = await embed_service.generate_embedding(request.query)
                query_cache.set_embedding(request.query, qemb)
            
            # Search
            logger.info("Searching database...")
            chunks = await search_service.search_similar(
                qemb,
                request.query,
                db,
                kitab_filter=request.kitab_filter,
                document_ids=request.document_ids
            )
            
            if chunks:
                query_cache.set_results(request.query, chunks, cache_key_filters)
        
        if not chunks:
            logger.warning("No chunks found")
            raise HTTPException(404, "Tidak ditemukan hadis relevan. Coba kata kunci lain.")
        
        logger.info(f"Found {len(chunks)} chunks")
        
        # OPTIMIZATION 3: Generate response (already optimized in LLM service)
        logger.info("Generating answer...")
        answer = await llm_service.generate_response(request.query, chunks)
        
        # Build sources
        sources = [
            Source(
                chunk_id=c['chunk_id'],
                text=c['text'][:200],
                page_number=c['page_number'],
                similarity_score=c.get('final_score', c['similarity']),
                kitab_name=c.get('kitab_name'),
                document_id=c['document_id']
            )
            for c in chunks[:5]  # Limit sources
        ]
        
        # Save to history (don't await - fire and forget for speed)
        sid = request.session_id or str(uuid.uuid4())
        asyncio.create_task(
            save_chat_history(sid, request.query, answer)
        )
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_query(sid, request.query, response_time)
        logger.info(f"✓ Response in {response_time:.0f}ms")
        
        return ChatResponse(answer=answer, sources=sources, session_id=sid)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Error: {str(e)}")

async def save_chat_history(session_id: str, query: str, answer: str):
    """Save chat history in background"""
    try:
        from app.database.connection import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            hist = ChatHistory(
                session_id=uuid.UUID(session_id) if len(session_id) == 36 else uuid.uuid4(),
                user_query=query,
                bot_response=answer,
                sources=[]
            )
            db.add(hist)
            await db.commit()
    except Exception as e:
        logger.error(f"Error saving history: {e}")

@router.post("/clear-cache")
async def clear_cache():
    """Clear query cache"""
    query_cache.clear()
    return {"message": "Cache cleared"}