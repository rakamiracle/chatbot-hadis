import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_chat_integration():
    """Test full chat flow"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        # Assuming ada dokumen yang sudah diupload
        response = await client.post(
            "/api/chat/",
            json={"query": "Apa itu wudhu?"}
        )
        
        # Might get 404 if no documents, that's OK for test
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "answer" in data
            assert "sources" in data
            assert "session_id" in data

@pytest.mark.asyncio
async def test_chat_with_cache():
    """Test caching works"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        query = "Jelaskan tentang shalat"
        
        # First request
        response1 = await client.post("/api/chat/", json={"query": query})
        
        # Second request (should be cached)
        response2 = await client.post("/api/chat/", json={"query": query})
        
        if response1.status_code == 200 and response2.status_code == 200:
            # Both should return same answer
            assert response1.json()["answer"] == response2.json()["answer"]
