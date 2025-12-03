from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.services.analytics_service import analytics_service
from app.models.analytics import FeedbackType, ErrorSeverity
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid

router = APIRouter()

# Schemas
class FeedbackRequest(BaseModel):
    session_id: str
    query: str
    response: str
    feedback_type: str  # 'thumbs_up' or 'thumbs_down'
    comment: Optional[str] = None
    chunks_count: int = 0

class FeedbackResponse(BaseModel):
    success: bool
    message: str

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    """Submit user feedback on a bot response"""
    try:
        # Validate feedback type
        if request.feedback_type not in ['thumbs_up', 'thumbs_down']:
            raise HTTPException(400, "Invalid feedback_type. Must be 'thumbs_up' or 'thumbs_down'")
        
        feedback_type = FeedbackType.thumbs_up if request.feedback_type == 'thumbs_up' else FeedbackType.thumbs_down
        
        # Parse session ID
        try:
            session_uuid = uuid.UUID(request.session_id)
        except ValueError:
            raise HTTPException(400, "Invalid session_id format")
        
        # Log feedback
        await analytics_service.log_feedback(
            db=db,
            session_id=session_uuid,
            query_text=request.query,
            response_text=request.response,
            feedback_type=feedback_type,
            comment=request.comment,
            chunks_count=request.chunks_count
        )
        
        return FeedbackResponse(
            success=True,
            message="Feedback submitted successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error submitting feedback: {str(e)}")

@router.get("/stats")
async def get_usage_stats(
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back")
):
    """Get usage statistics"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
        
        stats = await analytics_service.get_usage_stats(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
        
        return stats
    
    except Exception as e:
        raise HTTPException(500, f"Error fetching stats: {str(e)}")

@router.get("/performance")
async def get_performance_metrics(
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=90, description="Number of days to look back")
):
    """Get performance metrics"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
        
        metrics = await analytics_service.get_performance_metrics(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
        
        return metrics
    
    except Exception as e:
        raise HTTPException(500, f"Error fetching performance metrics: {str(e)}")

@router.get("/errors")
async def get_error_logs(
    db: AsyncSession = Depends(get_db),
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    limit: int = Query(50, ge=1, le=200, description="Number of errors to return")
):
    """Get error logs"""
    try:
        severity_enum = None
        if severity:
            try:
                severity_enum = ErrorSeverity[severity]
            except KeyError:
                raise HTTPException(400, f"Invalid severity. Must be one of: low, medium, high, critical")
        
        errors = await analytics_service.get_error_summary(
            db=db,
            severity=severity_enum,
            resolved=resolved,
            limit=limit
        )
        
        return {
            "errors": errors,
            "total": len(errors)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error fetching error logs: {str(e)}")

@router.get("/dashboard")
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, ge=1, le=90, description="Number of days for stats")
):
    """Get all dashboard data in one call"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
        
        # Get all data in parallel
        stats = await analytics_service.get_usage_stats(db, start_date, end_date)
        performance = await analytics_service.get_performance_metrics(db, start_date, end_date)
        errors = await analytics_service.get_error_summary(db, resolved=False, limit=10)
        
        return {
            "usage_stats": stats,
            "performance_metrics": performance,
            "recent_errors": errors,
            "period_days": days
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error fetching dashboard data: {str(e)}")
