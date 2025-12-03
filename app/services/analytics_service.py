from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from app.models.analytics import (
    AnalyticsQueryLog, AnalyticsFeedback, AnalyticsPerformance,
    AnalyticsErrorLog, AnalyticsUploadLog, FeedbackType, ErrorSeverity, UploadStatus
)
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import hashlib
import uuid

class AnalyticsService:
    """Centralized service for analytics and monitoring"""
    
    @staticmethod
    def _hash_text(text: str) -> str:
        """Hash text for privacy (MD5 is fine for non-security use)"""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def log_query(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        query_text: str,
        response_time_ms: float,
        embedding_time_ms: Optional[float] = None,
        search_time_ms: Optional[float] = None,
        llm_time_ms: Optional[float] = None,
        cache_hit: bool = False,
        chunks_found: int = 0,
        kitab_filter: Optional[str] = None,
        extra_data: Optional[Dict] = None
    ):
        """Log a query with performance metrics"""
        log = AnalyticsQueryLog(
            session_id=session_id,
            query_hash=self._hash_text(query_text),
            query_length=len(query_text),
            response_time_ms=response_time_ms,
            embedding_time_ms=embedding_time_ms,
            search_time_ms=search_time_ms,
            llm_time_ms=llm_time_ms,
            cache_hit=cache_hit,
            chunks_found=chunks_found,
            kitab_filter=kitab_filter,
            extra_data=extra_data
        )
        db.add(log)
        await db.commit()
    
    async def log_feedback(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        query_text: str,
        response_text: str,
        feedback_type: FeedbackType,
        comment: Optional[str] = None,
        chunks_count: int = 0
    ):
        """Log user feedback"""
        feedback = AnalyticsFeedback(
            session_id=session_id,
            query_hash=self._hash_text(query_text),
            response_hash=self._hash_text(response_text),
            feedback_type=feedback_type,
            comment=comment,
            chunks_count=chunks_count,
            response_length=len(response_text)
        )
        db.add(feedback)
        await db.commit()
    
    async def log_error(
        self,
        db: AsyncSession,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        endpoint: Optional[str] = None,
        session_id: Optional[uuid.UUID] = None,
        severity: ErrorSeverity = ErrorSeverity.medium,
        extra_data: Optional[Dict] = None
    ):
        """Log an error"""
        error = AnalyticsErrorLog(
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            endpoint=endpoint,
            session_id=session_id,
            severity=severity,
            extra_data=extra_data
        )
        db.add(error)
        await db.commit()
    
    async def log_upload(
        self,
        db: AsyncSession,
        filename: str,
        file_size_bytes: int,
        status: UploadStatus = UploadStatus.processing,
        total_pages: Optional[int] = None,
        total_chunks: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        extra_data: Optional[Dict] = None
    ) -> int:
        """Log a document upload, returns log ID"""
        upload = AnalyticsUploadLog(
            filename=filename,
            file_size_bytes=file_size_bytes,
            status=status,
            total_pages=total_pages,
            total_chunks=total_chunks,
            processing_time_ms=processing_time_ms,
            error_message=error_message,
            extra_data=extra_data
        )
        db.add(upload)
        await db.commit()
        await db.refresh(upload)
        return upload.id
    
    async def update_upload_status(
        self,
        db: AsyncSession,
        upload_id: int,
        status: UploadStatus,
        total_pages: Optional[int] = None,
        total_chunks: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Update upload status"""
        result = await db.execute(
            select(AnalyticsUploadLog).where(AnalyticsUploadLog.id == upload_id)
        )
        upload = result.scalar_one_or_none()
        
        if upload:
            upload.status = status
            upload.completed_at = datetime.utcnow()
            if total_pages:
                upload.total_pages = total_pages
            if total_chunks:
                upload.total_chunks = total_chunks
            if processing_time_ms:
                upload.processing_time_ms = processing_time_ms
            if error_message:
                upload.error_message = error_message
            
            await db.commit()
    
    async def get_usage_stats(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Get usage statistics"""
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Total queries
        query_count = await db.execute(
            select(func.count(AnalyticsQueryLog.id)).where(
                and_(
                    AnalyticsQueryLog.created_at >= start_date,
                    AnalyticsQueryLog.created_at <= end_date
                )
            )
        )
        total_queries = query_count.scalar()
        
        # Unique sessions
        session_count = await db.execute(
            select(func.count(func.distinct(AnalyticsQueryLog.session_id))).where(
                and_(
                    AnalyticsQueryLog.created_at >= start_date,
                    AnalyticsQueryLog.created_at <= end_date
                )
            )
        )
        unique_sessions = session_count.scalar()
        
        # Average response time
        avg_time = await db.execute(
            select(func.avg(AnalyticsQueryLog.response_time_ms)).where(
                and_(
                    AnalyticsQueryLog.created_at >= start_date,
                    AnalyticsQueryLog.created_at <= end_date
                )
            )
        )
        avg_response_time = avg_time.scalar() or 0
        
        # Cache hit rate
        cache_hits = await db.execute(
            select(func.count(AnalyticsQueryLog.id)).where(
                and_(
                    AnalyticsQueryLog.created_at >= start_date,
                    AnalyticsQueryLog.created_at <= end_date,
                    AnalyticsQueryLog.cache_hit == True
                )
            )
        )
        cache_hit_count = cache_hits.scalar()
        cache_hit_rate = cache_hit_count / total_queries if total_queries > 0 else 0
        
        # Total uploads
        upload_count = await db.execute(
            select(func.count(AnalyticsUploadLog.id)).where(
                and_(
                    AnalyticsUploadLog.created_at >= start_date,
                    AnalyticsUploadLog.created_at <= end_date
                )
            )
        )
        total_uploads = upload_count.scalar()
        
        # Feedback summary
        thumbs_up = await db.execute(
            select(func.count(AnalyticsFeedback.id)).where(
                and_(
                    AnalyticsFeedback.created_at >= start_date,
                    AnalyticsFeedback.created_at <= end_date,
                    AnalyticsFeedback.feedback_type == FeedbackType.thumbs_up
                )
            )
        )
        thumbs_up_count = thumbs_up.scalar()
        
        thumbs_down = await db.execute(
            select(func.count(AnalyticsFeedback.id)).where(
                and_(
                    AnalyticsFeedback.created_at >= start_date,
                    AnalyticsFeedback.created_at <= end_date,
                    AnalyticsFeedback.feedback_type == FeedbackType.thumbs_down
                )
            )
        )
        thumbs_down_count = thumbs_down.scalar()
        
        return {
            "total_queries": total_queries,
            "total_uploads": total_uploads,
            "unique_sessions": unique_sessions,
            "avg_response_time_ms": round(avg_response_time, 2),
            "cache_hit_rate": round(cache_hit_rate, 3),
            "feedback_summary": {
                "thumbs_up": thumbs_up_count,
                "thumbs_down": thumbs_down_count,
                "satisfaction_rate": round(
                    thumbs_up_count / (thumbs_up_count + thumbs_down_count)
                    if (thumbs_up_count + thumbs_down_count) > 0 else 0,
                    3
                )
            },
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
    
    async def get_performance_metrics(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Get performance metrics with percentiles"""
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Get all response times for percentile calculation
        result = await db.execute(
            select(
                AnalyticsQueryLog.response_time_ms,
                AnalyticsQueryLog.embedding_time_ms,
                AnalyticsQueryLog.search_time_ms,
                AnalyticsQueryLog.llm_time_ms
            ).where(
                and_(
                    AnalyticsQueryLog.created_at >= start_date,
                    AnalyticsQueryLog.created_at <= end_date
                )
            )
        )
        rows = result.all()
        
        if not rows:
            return {
                "avg_embedding_time_ms": 0,
                "avg_search_time_ms": 0,
                "avg_llm_time_ms": 0,
                "p50_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0
            }
        
        response_times = sorted([r.response_time_ms for r in rows if r.response_time_ms])
        embedding_times = [r.embedding_time_ms for r in rows if r.embedding_time_ms]
        search_times = [r.search_time_ms for r in rows if r.search_time_ms]
        llm_times = [r.llm_time_ms for r in rows if r.llm_time_ms]
        
        def percentile(data, p):
            if not data:
                return 0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f])
        
        return {
            "avg_embedding_time_ms": round(sum(embedding_times) / len(embedding_times), 2) if embedding_times else 0,
            "avg_search_time_ms": round(sum(search_times) / len(search_times), 2) if search_times else 0,
            "avg_llm_time_ms": round(sum(llm_times) / len(llm_times), 2) if llm_times else 0,
            "p50_response_time_ms": round(percentile(response_times, 50), 2),
            "p95_response_time_ms": round(percentile(response_times, 95), 2),
            "p99_response_time_ms": round(percentile(response_times, 99), 2),
            "total_samples": len(rows)
        }
    
    async def get_error_summary(
        self,
        db: AsyncSession,
        severity: Optional[ErrorSeverity] = None,
        resolved: Optional[bool] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get error logs"""
        
        query = select(AnalyticsErrorLog).order_by(desc(AnalyticsErrorLog.created_at))
        
        conditions = []
        if severity:
            conditions.append(AnalyticsErrorLog.severity == severity)
        if resolved is not None:
            conditions.append(AnalyticsErrorLog.resolved == resolved)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.limit(limit)
        
        result = await db.execute(query)
        errors = result.scalars().all()
        
        return [
            {
                "id": e.id,
                "error_type": e.error_type,
                "error_message": e.error_message,
                "endpoint": e.endpoint,
                "severity": e.severity.value,
                "resolved": e.resolved,
                "created_at": e.created_at.isoformat()
            }
            for e in errors
        ]

# Global instance
analytics_service = AnalyticsService()
