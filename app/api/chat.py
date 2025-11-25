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
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    embed = EmbeddingService()
    search = VectorSearch()
    llm = LLMService()
    
    qemb = await embed.generate_embedding(request.query)
    
    # Search dengan filter
    chunks = await search.search_similar(
        qemb, 
        db,
        kitab_filter=request.kitab_filter,
        document_ids=request.document_ids
    )
    
    if not chunks:
        raise HTTPException(404, "No relevant hadis found")
    
    answer = await llm.generate_response(request.query, chunks)
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
    
    sid = request.session_id or str(uuid.uuid4())
    hist = ChatHistory(
        session_id=uuid.UUID(sid) if request.session_id else uuid.uuid4(),
        user_query=request.query,
        bot_response=answer,
        sources=[]
    )
    db.add(hist)
    await db.commit()
    
    return ChatResponse(answer=answer, sources=sources, session_id=sid)