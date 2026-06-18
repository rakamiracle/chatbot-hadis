from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database.connection import Base
from datetime import datetime

# ========== TABLE 1: KITAB (Daftar Kitab) ==========
class Kitab(Base):
    __tablename__ = "kitab"
    
    id = Column(Integer, primary_key=True)
    nama_kitab = Column(String(255))
    
    # Relasi ke hadis
    hadis = relationship("Hadis", back_populates="kitab")


# ========== TABLE 2: BAB (Daftar Bab/Chapter) ==========
class Bab(Base):
    __tablename__ = "bab"
    
    id = Column(Integer, primary_key=True)
    Bab = Column(String(100), unique=True)
    
    # Relasi ke hadis
    hadis = relationship("Hadis", back_populates="bab")


# ========== TABLE 3: HADIS (Data Hadis) ==========
class Hadis(Base):
    __tablename__ = "muwatho_malik"
    
    id = Column(Integer, primary_key=True)
    
    # Data hadis
    arab = Column(Text, nullable=False)          # Teks Arab
    terjemah = Column(Text, nullable=False)      # Terjemahan Indonesia
    
    # Foreign Keys (referensi ke kitab & bab)
    id_bab = Column(Integer, ForeignKey("bab.id"))
    id_kitab = Column(Integer, ForeignKey("kitab.id"), default=3)
    
    # Vector embedding (untuk search)
    embedding = Column(Vector(512), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relasi balik
    kitab = relationship("Kitab", back_populates="hadis")
    bab = relationship("Bab", back_populates="hadis")