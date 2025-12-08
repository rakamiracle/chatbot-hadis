from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.schemas.chat import ChatRequest, ChatResponse, Source
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import VectorSearch
from app.services.llm_service import LLMService
from app.services.query_cache import query_cache
from app.services.analytics_service import analytics_service
from app.models.chat_history import ChatHistory
from app.models.analytics import ErrorSeverity
from app.utils.logger import logger, log_query
from datetime import datetime
import uuid
import asyncio
import time

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    start_time = datetime.utcnow()
    start_time_ms = time.time() * 1000
    
    # Timing variables
    embedding_time_ms = None
    search_time_ms = None
    llm_time_ms = None
    cache_hit = False
    
    try:
        logger.info(f"Query: {request.query[:100]}")
        
        # OPTIMIZATION: Reuse singleton instances (no re-initialization)
        embed_service = EmbeddingService()  # Singleton pattern
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
            cache_hit = True
        else:
            # OPTIMIZATION 2: Check embedding cache
            qemb = query_cache.get_embedding(request.query)
            
            if qemb:
                logger.info("✓ Embedding cache hit")
            else:
                logger.info("Generating embedding...")
                embed_start = time.time() * 1000
                qemb = await embed_service.generate_embedding(request.query)
                embedding_time_ms = time.time() * 1000 - embed_start
                query_cache.set_embedding(request.query, qemb)
            
            # Search
            logger.info("Searching database...")
            search_start = time.time() * 1000
            chunks = await search_service.search_similar(
                qemb,
                request.query,
                db,
                kitab_filter=request.kitab_filter,
                document_ids=request.document_ids
            )
            search_time_ms = time.time() * 1000 - search_start
            
            if chunks:
                query_cache.set_results(request.query, chunks, cache_key_filters)
        
        if not chunks:
            logger.warning("No chunks found")
            # Return friendly message instead of error
            no_results_message = (
                "Maaf, saya tidak menemukan hadis yang relevan dengan pertanyaan Anda. "
                "Silakan coba dengan kata kunci yang berbeda atau lebih spesifik."
            )
            return ChatResponse(
                answer=no_results_message,
                sources=[],
                session_id=request.session_id or str(uuid.uuid4())
            )
        
        logger.info(f"Found {len(chunks)} chunks")
        
        # OPTIMIZATION 3: Generate response (already optimized in LLM service)
        logger.info("Generating answer...")
        llm_start = time.time() * 1000
        answer = await llm_service.generate_response(request.query, chunks, force_arabic=request.force_arabic)
        llm_time_ms = time.time() * 1000 - llm_start
        
        # Build sources dengan Arab
        sources = []
        for c in chunks[:5]:
            meta = c.get('metadata', {})
            
            source_data = {
                "chunk_id": c['chunk_id'],
                "text": c['text'][:200],
                "page_number": c['page_number'],
                "similarity_score": c.get('final_score', c['similarity']),
                "kitab_name": c.get('kitab_name'),
                "document_id": c['document_id']
            }
            
            # ✨ Include Arab jika ada
            if meta.get('arab'):
                source_data['arabic_text'] = meta['arab']
            
            if meta.get('perawi'):
                source_data['perawi'] = meta['perawi']
            
            if meta.get('nomor_hadis'):
                source_data['hadis_number'] = meta['nomor_hadis']
            
            sources.append(Source(**source_data))
        
        # Save to history (don't await - fire and forget for speed)
        sid = request.session_id or str(uuid.uuid4())
        asyncio.create_task(
            save_chat_history(sid, request.query, answer)
        )
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        log_query(sid, request.query, response_time)
        logger.info(f"✓ Response in {response_time:.0f}ms")
        
        # Log analytics (fire and forget) - Don't pass db, let analytics create its own session
        asyncio.create_task(
            log_analytics_async(
                session_id=uuid.UUID(sid) if len(sid) == 36 else uuid.uuid4(),
                query_text=request.query,
                response_time_ms=response_time,
                embedding_time_ms=embedding_time_ms,
                search_time_ms=search_time_ms,
                llm_time_ms=llm_time_ms,
                cache_hit=cache_hit,
                chunks_found=len(chunks),
                kitab_filter=request.kitab_filter
            )
        )
        
        return ChatResponse(answer=answer, sources=sources, session_id=sid)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        
        # Log error to analytics (fire and forget)
        try:
            asyncio.create_task(
                analytics_service.log_error(
                    db=db,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    endpoint="/api/chat",
                    severity=ErrorSeverity.high
                )
            )
        except:
            pass  # Don't fail if analytics logging fails
        
        raise HTTPException(500, f"Error: {str(e)}")

async def save_chat_history(session_id: str, query: str, answer: str):
    """Save chat history in background with embeddings"""
    try:
        from app.database.connection import AsyncSessionLocal
        
        # Generate embeddings
        embed_service = EmbeddingService()
        
        # Truncate texts if needed (max ~2000 chars)
        query_text = query[:2000] if len(query) > 2000 else query
        answer_text = answer[:2000] if len(answer) > 2000 else answer
        combined_text = f"Q: {query_text} A: {answer_text}"
        if len(combined_text) > 2000:
            combined_text = combined_text[:2000]
        
        # Generate all three embeddings
        query_embedding = await embed_service.generate_embedding(query_text)
        response_embedding = await embed_service.generate_embedding(answer_text)
        combined_embedding = await embed_service.generate_embedding(combined_text)
        
        async with AsyncSessionLocal() as db:
            hist = ChatHistory(
                session_id=uuid.UUID(session_id) if len(session_id) == 36 else uuid.uuid4(),
                user_query=query,
                bot_response=answer,
                sources=[],
                query_embedding=query_embedding,
                response_embedding=response_embedding,
                combined_embedding=combined_embedding
            )
            db.add(hist)
            await db.commit()
            logger.info(f"✓ Chat history saved with embeddings")
    except Exception as e:
        logger.error(f"Error saving history: {e}")

async def log_analytics_async(
    session_id: uuid.UUID,
    query_text: str,
    response_time_ms: float,
    embedding_time_ms: float = None,
    search_time_ms: float = None,
    llm_time_ms: float = None,
    cache_hit: bool = False,
    chunks_found: int = 0,
    kitab_filter: str = None
):
    """Log analytics in background with its own session"""
    try:
        from app.database.connection import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await analytics_service.log_query(
                db=db,
                session_id=session_id,
                query_text=query_text,
                response_time_ms=response_time_ms,
                embedding_time_ms=embedding_time_ms,
                search_time_ms=search_time_ms,
                llm_time_ms=llm_time_ms,
                cache_hit=cache_hit,
                chunks_found=chunks_found,
                kitab_filter=kitab_filter
            )
    except Exception as e:
        logger.error(f"Error logging analytics: {e}")

@router.post("/clear-cache")
async def clear_cache():
    """Clear query cache"""
    query_cache.clear()
    return {"message": "Cache cleared"}