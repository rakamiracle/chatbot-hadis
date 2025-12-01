import pytest
import os
from app.services.pdf_processor import PDFProcessor

@pytest.mark.asyncio
async def test_extract_text_valid_pdf():
    """Test ekstraksi text dari PDF valid"""
    processor = PDFProcessor()
    
    # Assuming test PDF exists
    test_pdf = "tests/fixtures/sample_hadis.pdf"
    
    if not os.path.exists(test_pdf):
        pytest.skip("Sample PDF not found")
    
    result = await processor.extract_text(test_pdf)
    
    assert result is not None
    assert 'pages' in result
    assert 'total_pages' in result
    assert result['total_pages'] > 0
    assert len(result['pages']) == result['total_pages']

@pytest.mark.asyncio
async def test_extract_text_invalid_path():
    """Test dengan path yang tidak ada"""
    processor = PDFProcessor()
    
    with pytest.raises(Exception):
        await processor.extract_text("nonexistent.pdf")
