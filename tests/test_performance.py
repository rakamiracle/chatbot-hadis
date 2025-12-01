import pytest
import time
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_response_time_benchmark():
    """Benchmark response time"""
    
    queries = [
        "Apa itu wudhu?",
        "Bagaimana cara shalat?",
        "Siapa perawi hadis tentang puasa?",
        "Apa hukum zakat?",
        "Berapa nisab zakat?"
    ]
    
    results = []
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        for query in queries:
            start = time.time()
            response = await client.post("/api/chat/", json={"query": query})
            duration = time.time() - start
            
            results.append({
                "query": query,
                "duration": duration,
                "status": response.status_code
            })
    
    # Calculate stats
    durations = [r["duration"] for r in results if r["status"] == 200]
    
    if durations:
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        print(f"\n=== Performance Benchmark ===")
        print(f"Average: {avg_duration:.2f}s")
        print(f"Min: {min_duration:.2f}s")
        print(f"Max: {max_duration:.2f}s")
        
        # Assert performance criteria
        assert avg_duration < 5.0, "Average response time > 5s"
        assert max_duration < 10.0, "Max response time > 10s"
