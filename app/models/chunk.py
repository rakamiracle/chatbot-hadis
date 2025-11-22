from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime

class HadisChunk(Base):
    __tablename__ = "hadis_chunks"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("hadis_documents.id", ondelete="CASCADE"))
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer)
    page_number = Column(Integer)
    embedding = Column(Vector(384))
    chunk_metadata = Column(JSONB)  # ← Ganti dari metadata ke chunk_metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    document = relationship("HadisDocument", back_populates="chunks")