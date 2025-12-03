from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector
from app.database.connection import Base
from datetime import datetime
import uuid

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), default=uuid.uuid4, index=True)
    user_query = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    sources = Column(JSONB)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Vector embeddings for semantic search
    query_embedding = Column(Vector(384))  # Embedding for user query
    response_embedding = Column(Vector(384))  # Embedding for bot response
    combined_embedding = Column(Vector(384))  # Embedding for full conversation