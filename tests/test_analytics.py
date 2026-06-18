import pytest
import uuid
from datetime import datetime
from app.services.analytics_service import analytics_service
from app.models.analytics import FeedbackType, ErrorSeverity, UploadStatus

@pytest.mark.asyncio
async def test_log_query(db_session):
    """Test logging a query"""
    session_id = uuid.uuid4()
    
    await analytics_service.log_query(
        db=db_session,
        session_id=session_id,
        query_text="test query",
        response_time_ms=1500.5,
        embedding_time_ms=150.0,
        search_time_ms=200.0,
        llm_time_ms=1000.0,
        cache_hit=False,
        chunks_found=5,
        kitab_filter="Sahih Bukhari"
    )
    
    # Verify it was logged
    stats = await analytics_service.get_usage_stats(db_session)
    assert stats['total_queries'] >= 1

@pytest.mark.asyncio
async def test_log_feedback(db_session):
    """Test logging user feedback"""
    session_id = uuid.uuid4()
    
    await analytics_service.log_feedback(
        db=db_session,
        session_id=session_id,
        query_text="test query",
        response_text="test response",
        feedback_type=FeedbackType.thumbs_up,
        chunks_count=3
    )
    
    # Verify feedback was logged
    stats = await analytics_service.get_usage_stats(db_session)
    assert stats['feedback_summary']['thumbs_up'] >= 1

@pytest.mark.asyncio
async def test_log_error(db_session):
    """Test logging an error"""
    await analytics_service.log_error(
        db=db_session,
        error_type="TestError",
        error_message="This is a test error",
        endpoint="/api/test",
        severity=ErrorSeverity.medium
    )
    
    # Verify error was logged
    errors = await analytics_service.get_error_summary(db_session, limit=10)
    assert len(errors) >= 1
    assert errors[0]['error_type'] == "TestError"

@pytest.mark.asyncio
async def test_log_upload(db_session):
    """Test logging an upload"""
    upload_id = await analytics_service.log_upload(
        db=db_session,
        filename="test.pdf",
        file_size_bytes=1024000,
        status=UploadStatus.processing
    )
    
    assert upload_id is not None
    
    # Update status
    await analytics_service.update_upload_status(
        db=db_session,
        upload_id=upload_id,
        status=UploadStatus.success,
        total_pages=10,
        total_chunks=50,
        processing_time_ms=5000
    )

@pytest.mark.asyncio
async def test_get_usage_stats(db_session):
    """Test getting usage statistics"""
    # Log some data
    session_id = uuid.uuid4()
    
    await analytics_service.log_query(
        db=db_session,
        session_id=session_id,
        query_text="test query 1",
        response_time_ms=2000.0,
        cache_hit=False,
        chunks_found=5
    )
    
    await analytics_service.log_query(
        db=db_session,
        session_id=session_id,
        query_text="test query 2",
        response_time_ms=500.0,
        cache_hit=True,
        chunks_found=5
    )
    
    # Get stats
    stats = await analytics_service.get_usage_stats(db_session)
    
    assert stats['total_queries'] >= 2
    assert stats['avg_response_time_ms'] > 0
    assert 0 <= stats['cache_hit_rate'] <= 1

@pytest.mark.asyncio
async def test_get_performance_metrics(db_session):
    """Test getting performance metrics"""
    # Log some queries with timing
    session_id = uuid.uuid4()
    
    for i in range(5):
        await analytics_service.log_query(
            db=db_session,
            session_id=session_id,
            query_text=f"test query {i}",
            response_time_ms=2000.0 + i * 100,
            embedding_time_ms=150.0,
            search_time_ms=200.0,
            llm_time_ms=1500.0,
            cache_hit=False,
            chunks_found=5
        )
    
    # Get performance metrics
    metrics = await analytics_service.get_performance_metrics(db_session)
    
    assert metrics['avg_embedding_time_ms'] > 0
    assert metrics['avg_search_time_ms'] > 0
    assert metrics['avg_llm_time_ms'] > 0
    assert metrics['p50_response_time_ms'] > 0
    assert metrics['p95_response_time_ms'] >= metrics['p50_response_time_ms']
    assert metrics['p99_response_time_ms'] >= metrics['p95_response_time_ms']

@pytest.mark.asyncio
async def test_feedback_satisfaction_rate(db_session):
    """Test satisfaction rate calculation"""
    session_id = uuid.uuid4()
    
    # Add positive feedback
    for i in range(8):
        await analytics_service.log_feedback(
            db=db_session,
            session_id=session_id,
            query_text=f"query {i}",
            response_text=f"response {i}",
            feedback_type=FeedbackType.thumbs_up,
            chunks_count=3
        )
    
    # Add negative feedback
    for i in range(2):
        await analytics_service.log_feedback(
            db=db_session,
            session_id=session_id,
            query_text=f"query {i}",
            response_text=f"response {i}",
            feedback_type=FeedbackType.thumbs_down,
            chunks_count=3
        )
    
    # Get stats
    stats = await analytics_service.get_usage_stats(db_session)
    
    assert stats['feedback_summary']['thumbs_up'] >= 8
    assert stats['feedback_summary']['thumbs_down'] >= 2
    assert 0.7 <= stats['feedback_summary']['satisfaction_rate'] <= 0.9

@pytest.mark.asyncio
async def test_error_filtering(db_session):
    """Test error filtering by severity"""
    # Log errors with different severities
    await analytics_service.log_error(
        db=db_session,
        error_type="LowError",
        error_message="Low severity error",
        severity=ErrorSeverity.low
    )
    
    await analytics_service.log_error(
        db=db_session,
        error_type="HighError",
        error_message="High severity error",
        severity=ErrorSeverity.high
    )
    
    # Get high severity errors only
    high_errors = await analytics_service.get_error_summary(
        db_session,
        severity=ErrorSeverity.high
    )
    
    assert len(high_errors) >= 1
    assert all(e['severity'] == 'high' for e in high_errors)
