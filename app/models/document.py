from sqlalchemy import Column, Integer, String, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database.connection import Base
from datetime import datetime
import enum

class DocumentStatus(str, enum.Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class HadisDocument(Base):
    __tablename__ = "hadis_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    total_pages = Column(Integer)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PROCESSING)
    
    # Metadata dokumen
    kitab_name = Column(String)  # Nama kitab
    pengarang = Column(String)  # Pengarang
    penerbit = Column(String)
    tahun_terbit = Column(String)
    doc_metadata = Column(JSONB)  # Metadata tambahan
    
    chunks = relationship("HadisChunk", back_populates="document", cascade="all, delete-orphan")