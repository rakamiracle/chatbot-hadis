from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database.connection import Base
from datetime import datetime
import uuid
import enum

class FeedbackType(enum.Enum):
    thumbs_up = "thumbs_up"
    thumbs_down = "thumbs_down"

class AnalyticsQueryLog(Base):
    """Track all queries with detailed performance metrics"""
    __tablename__ = "analytics_query_log"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), index=True)
    query_hash = Column(String(64), index=True)  # MD5 hash for privacy
    query_length = Column(Integer)  # Store length instead of full text
    
    # Performance metrics
    response_time_ms = Column(Float)
    embedding_time_ms = Column(Float, nullable=True)
    search_time_ms = Column(Float, nullable=True)
    llm_time_ms = Column(Float, nullable=True)
    
    # Query details
    cache_hit = Column(Boolean, default=False)
    chunks_found = Column(Integer)
    kitab_filter = Column(String(100), nullable=True)
    
    # Extra data
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class AnalyticsFeedback(Base):
    """Track user feedback on bot responses"""
    __tablename__ = "analytics_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), index=True)
    query_hash = Column(String(64))  # Reference to query
    response_hash = Column(String(64))  # Hash of response
    
    feedback_type = Column(SQLEnum(FeedbackType), nullable=False)
    comment = Column(Text, nullable=True)
    
    # Context
    chunks_count = Column(Integer)  # How many sources were shown
    response_length = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class AnalyticsPerformance(Base):
    """Track system performance metrics"""
    __tablename__ = "analytics_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), index=True)
    metric_value = Column(Float)
    metric_unit = Column(String(20))  # 'ms', 'seconds', 'count', etc.
    
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class ErrorSeverity(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class AnalyticsErrorLog(Base):
    """Track errors and exceptions"""
    __tablename__ = "analytics_error_log"
    
    id = Column(Integer, primary_key=True, index=True)
    error_type = Column(String(100), index=True)
    error_message = Column(Text)
    stack_trace = Column(Text, nullable=True)
    
    endpoint = Column(String(200), nullable=True)
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    severity = Column(SQLEnum(ErrorSeverity), default=ErrorSeverity.medium, index=True)
    resolved = Column(Boolean, default=False, index=True)
    
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

class UploadStatus(enum.Enum):
    processing = "processing"
    success = "success"
    failed = "failed"

class AnalyticsUploadLog(Base):
    """Track document uploads"""
    __tablename__ = "analytics_upload_log"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    file_size_bytes = Column(Integer)
    
    total_pages = Column(Integer, nullable=True)
    total_chunks = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    status = Column(SQLEnum(UploadStatus), default=UploadStatus.processing, index=True)
    error_message = Column(Text, nullable=True)
    
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
