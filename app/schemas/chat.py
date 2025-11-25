from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    kitab_filter: Optional[str] = None  # Filter per kitab
    document_ids: Optional[List[int]] = None  # Filter per dokumen

class Source(BaseModel):
    chunk_id: int
    text: str
    page_number: int
    similarity_score: float
    kitab_name: Optional[str] = None  # Tambah info kitab
    document_id: int

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str