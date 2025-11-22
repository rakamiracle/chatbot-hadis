from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class Source(BaseModel):
    chunk_id: int
    text: str
    page_number: int
    similarity_score: float

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str