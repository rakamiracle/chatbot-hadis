# Monitoring & Analytics System

## Overview

Comprehensive monitoring and analytics system untuk Chatbot Hadis yang meliputi:
- 📊 Usage Statistics
- 💬 User Feedback (Thumbs Up/Down)
- 🚨 Error Tracking
- ⚡ Performance Metrics

---

## Features

### 1. Usage Statistics
- Total queries per period
- Unique sessions
- Average response time
- Cache hit rate
- Upload statistics

### 2. User Feedback
- Thumbs up/down buttons pada setiap response
- Satisfaction rate calculation
- Optional comments
- Feedback trends over time

### 3. Error Tracking
- Automatic error logging
- Severity levels (low, medium, high, critical)
- Stack traces
- Error resolution tracking

### 4. Performance Metrics
- Embedding generation time
- Vector search time
- LLM generation time
- Response time percentiles (P50, P95, P99)
- Performance trends

---

## Installation

### 1. Create Analytics Tables

```bash
python scripts/add_analytics_tables.py
```

This will create:
- `analytics_query_log` - Query performance tracking
- `analytics_feedback` - User feedback
- `analytics_performance` - Performance metrics
- `analytics_error_log` - Error logs
- `analytics_upload_log` - Upload tracking

### 2. Restart Application

```bash
# Restart FastAPI
python run.py

# Run Streamlit (in another terminal)
streamlit run streamlit_app.py
```

---

## API Endpoints

### Submit Feedback
```http
POST /api/analytics/feedback
Content-Type: application/json

{
  "session_id": "uuid-string",
  "query": "user query",
  "response": "bot response",
  "feedback_type": "thumbs_up",  // or "thumbs_down"
  "comment": "optional comment",
  "chunks_count": 3
}
```

### Get Usage Statistics
```http
GET /api/analytics/stats?days=30
```

Response:
```json
{
  "total_queries": 1234,
  "total_uploads": 56,
  "unique_sessions": 89,
  "avg_response_time_ms": 2500,
  "cache_hit_rate": 0.45,
  "feedback_summary": {
    "thumbs_up": 234,
    "thumbs_down": 12,
    "satisfaction_rate": 0.951
  }
}
```

### Get Performance Metrics
```http
GET /api/analytics/performance?days=7
```

Response:
```json
{
  "avg_embedding_time_ms": 150,
  "avg_search_time_ms": 200,
  "avg_llm_time_ms": 2000,
  "p50_response_time_ms": 2100,
  "p95_response_time_ms": 4500,
  "p99_response_time_ms": 8000,
  "total_samples": 500
}
```

### Get Error Logs
```http
GET /api/analytics/errors?severity=high&resolved=false&limit=50
```

### Get Dashboard Data
```http
GET /api/analytics/dashboard?days=7
```

Returns combined stats, performance, and errors in one call.

---

## Frontend Integration

### Streamlit Main App

Feedback buttons automatically appear after each bot response:
- 👍 Thumbs Up - Jawaban membantu
- 👎 Thumbs Down - Jawaban kurang membantu

Feedback is sent to backend automatically.

### Analytics Dashboard

Access via: `http://localhost:8501/analytics_dashboard`

Features:
- Real-time usage statistics
- Performance charts
- Feedback visualization
- Error monitoring
- Export data to CSV

---

## Usage Examples

### Programmatic Access

```python
from app.services.analytics_service import analytics_service
from app.models.analytics import FeedbackType, ErrorSeverity
import uuid

# Log a query
await analytics_service.log_query(
    db=db,
    session_id=uuid.uuid4(),
    query_text="apa itu wudhu",
    response_time_ms=2500.0,
    embedding_time_ms=150.0,
    search_time_ms=200.0,
    llm_time_ms=2000.0,
    cache_hit=False,
    chunks_found=5,
    kitab_filter="Sahih Bukhari"
)

# Log feedback
await analytics_service.log_feedback(
    db=db,
    session_id=uuid.uuid4(),
    query_text="apa itu wudhu",
    response_text="Wudhu adalah...",
    feedback_type=FeedbackType.thumbs_up,
    chunks_count=3
)

# Log error
await analytics_service.log_error(
    db=db,
    error_type="LLMTimeout",
    error_message="LLM took too long to respond",
    endpoint="/api/chat",
    severity=ErrorSeverity.high
)

# Get statistics
stats = await analytics_service.get_usage_stats(db)
performance = await analytics_service.get_performance_metrics(db)
errors = await analytics_service.get_error_summary(db, severity=ErrorSeverity.high)
```

---

## Database Schema

### analytics_query_log
- `id` - Primary key
- `session_id` - UUID (indexed)
- `query_hash` - MD5 hash for privacy
- `query_length` - Length of query
- `response_time_ms` - Total response time
- `embedding_time_ms` - Embedding time
- `search_time_ms` - Search time
- `llm_time_ms` - LLM time
- `cache_hit` - Boolean
- `chunks_found` - Number of chunks
- `kitab_filter` - Filter used
- `metadata` - JSONB
- `created_at` - Timestamp (indexed)

### analytics_feedback
- `id` - Primary key
- `session_id` - UUID (indexed)
- `query_hash` - Reference to query
- `response_hash` - Hash of response
- `feedback_type` - Enum (thumbs_up, thumbs_down)
- `comment` - Optional text
- `chunks_count` - Number of sources
- `response_length` - Length of response
- `created_at` - Timestamp (indexed)

### analytics_error_log
- `id` - Primary key
- `error_type` - String (indexed)
- `error_message` - Text
- `stack_trace` - Text
- `endpoint` - String
- `session_id` - UUID (indexed)
- `severity` - Enum (low, medium, high, critical)
- `resolved` - Boolean (indexed)
- `metadata` - JSONB
- `created_at` - Timestamp (indexed)
- `resolved_at` - Timestamp

---

## Privacy Considerations

### Data Protection
- Query text is **hashed** (MD5) for privacy
- Only query length is stored, not full text
- Response text is also hashed
- No PII is stored

### Data Retention
- Default retention: 90 days
- Automatic cleanup can be scheduled
- Users can opt-out of tracking (future feature)

---

## Performance Impact

### Overhead
- Analytics logging is **async** (fire-and-forget)
- No blocking of main request
- Minimal performance impact (<5ms)

### Database
- Proper indexes for fast queries
- Partitioning recommended for large datasets
- Regular cleanup of old data

---

## Monitoring Best Practices

### 1. Track Key Metrics
- Response time trends
- Cache hit rate
- Error rates
- User satisfaction

### 2. Set Alerts
- P95 response time > 5 seconds
- Error rate > 5%
- Satisfaction rate < 80%

### 3. Regular Review
- Weekly performance review
- Monthly feedback analysis
- Quarterly error pattern analysis

### 4. Act on Insights
- Optimize slow queries
- Fix recurring errors
- Improve responses with low satisfaction

---

## Troubleshooting

### Analytics not logging
1. Check database connection
2. Verify tables exist: `python scripts/add_analytics_tables.py`
3. Check logs for errors

### Dashboard not loading
1. Ensure FastAPI is running
2. Check API_URL in `pages/analytics_dashboard.py`
3. Verify analytics endpoints are accessible

### Feedback not submitting
1. Check browser console for errors
2. Verify session_id is valid UUID
3. Check API logs for errors

---

## Future Enhancements

### Planned Features
- [ ] Real-time dashboard with WebSocket
- [ ] Email alerts for critical errors
- [ ] A/B testing framework
- [ ] User journey tracking
- [ ] Export to external analytics (Google Analytics, Mixpanel)
- [ ] Automated performance reports
- [ ] Anomaly detection

### Integration Ideas
- Sentry for error tracking
- Prometheus for metrics
- Grafana for visualization
- DataDog for monitoring

---

## Testing

Run analytics tests:
```bash
pytest tests/test_analytics.py -v
```

Tests cover:
- Query logging
- Feedback submission
- Error tracking
- Statistics calculation
- Performance metrics
- Data filtering

---

## API Documentation

Full API documentation available at:
```
http://localhost:8000/docs#/analytics
```

Interactive API testing via Swagger UI.

---

## Support

For issues or questions:
1. Check logs: `data/logs/app.log`
2. Review error logs in dashboard
3. Check database connectivity
4. Verify all dependencies installed

---

## Summary

The monitoring and analytics system provides:
✅ Comprehensive usage tracking
✅ User feedback collection
✅ Error monitoring
✅ Performance metrics
✅ Beautiful dashboard
✅ Privacy-focused design
✅ Minimal performance overhead
✅ Easy integration

Start tracking your chatbot's performance today! 🚀
