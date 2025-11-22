from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.schemas.chat import ChatRequest, ChatResponse, Source
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import VectorSearch
from app.services.llm_service import LLMService
from app.models.chat_history import ChatHistory
import uuid

router = APIRouter()
embedding_service = EmbeddingService()
vector_search = VectorSearch()
llm_service = LLMService()

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Generate query embedding
        query_embedding = await embedding_service.generate_embedding(request.query)
        
        # Search similar chunks
        similar_chunks = await vector_search.search_similar(query_embedding, db)
        
        if not similar_chunks:
            raise HTTPException(404, "Tidak ditemukan hadis yang relevan")
        
        # Generate response from LLM
        answer = await llm_service.generate_response(request.query, similar_chunks)
        
        # Prepare sources
        sources = [
            Source(
                chunk_id=chunk['chunk_id'],
                text=chunk['text'][:200] + "...",
                page_number=chunk['page_number'],
                similarity_score=chunk['similarity']
            )
            for chunk in similar_chunks
        ]
        
        # Save to history
        session_id = request.session_id or str(uuid.uuid4())
        history = ChatHistory(
            session_id=session_id,
            user_query=request.query,
            bot_response=answer,
            sources=[s.dict() for s in sources]
        )
        db.add(history)
        await db.commit()
        
        return ChatResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")