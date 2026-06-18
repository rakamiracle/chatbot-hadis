import pytest
from httpx import AsyncClient
from app.main import app
import os

@pytest.mark.asyncio
async def test_upload_pdf_integration():
    """Test full upload flow"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        # Create sample PDF for testing
        test_pdf = "tests/fixtures/sample_hadis.pdf"
        
        if not os.path.exists(test_pdf):
            pytest.skip("Sample PDF not found")
        
        with open(test_pdf, "rb") as f:
            response = await client.post(
                "/api/upload/",
                files={"file": ("test.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "document_id" in data
        assert "filename" in data
        assert data["status"] in ["completed", "processing"]

@pytest.mark.asyncio
async def test_upload_invalid_file():
    """Test upload file non-PDF"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        response = await client.post(
            "/api/upload/",
            files={"file": ("test.txt", b"not a pdf", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "Only PDF" in response.json()["detail"]
