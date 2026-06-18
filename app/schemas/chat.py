from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    kitab_filter: Optional[str] = None
    document_ids: Optional[List[int]] = None
    force_arabic: Optional[bool] = None

class Source(BaseModel):
    chunk_id: int
    text: str
    page_number: int
    similarity_score: float
    kitab_name: Optional[str] = None
    document_id: int

    # 🔥 Metadata hadis yang ditampilkan
    arabic_text: Optional[str] = None
    perawi: Optional[str] = None
    hadis_number: Optional[str] = None
    
    # 🔥 TAMBAHAN BARU: Bab dan Kitab dari metadata chunk
    bab: Optional[str] = None
    bab_nomor: Optional[str] = None
    kitab_metadata: Optional[str] = None  # Kitab dari metadata chunk
    derajat: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str
    include_arabic: bool = False