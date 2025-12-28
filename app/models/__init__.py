"""
Models package initialization
Import all models here to ensure SQLAlchemy can resolve relationships
"""

from app.models.document import HadisDocument, DocumentStatus
from app.models.chunk import HadisChunk
from app.models.chat_history import ChatHistory
from app.models.analytics import (
    AnalyticsQueryLog,
    AnalyticsErrorLog,
    AnalyticsFeedback,
    AnalyticsPerformance,
    AnalyticsUploadLog,
    ErrorSeverity,
    FeedbackType,
    UploadStatus
)

__all__ = [
    "HadisDocument",
    "DocumentStatus", 
    "HadisChunk",
    "ChatHistory",
    "AnalyticsQueryLog",
    "AnalyticsErrorLog",
    "AnalyticsFeedback",
    "AnalyticsPerformance",
    "AnalyticsUploadLog",
    "ErrorSeverity",
    "FeedbackType",
    "UploadStatus"
]

