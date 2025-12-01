import pytest
from app.services.chunker import HadisChunker

@pytest.mark.asyncio
async def test_chunk_text_basic():
    """Test basic chunking"""
    chunker = HadisChunker(chunk_size=100, overlap=20)
    
    text = "Ini adalah hadis tentang shalat. " * 50  # Long text
    chunks = await chunker.chunk_text(text, page_number=1)
    
    assert len(chunks) > 0
    assert all(c['page_number'] == 1 for c in chunks)
    assert all('text' in c for c in chunks)
    assert all('chunk_index' in c for c in chunks)

@pytest.mark.asyncio
async def test_chunk_with_hadis_number():
    """Test chunking dengan nomor hadis"""
    chunker = HadisChunker()
    
    text = """
    Hadis 123: Dari Abu Hurairah, Rasulullah bersabda...
    
    Hadis 124: Dari Aisyah, Rasulullah bersabda...
    """
    
    chunks = await chunker.chunk_text(text, page_number=1)
    
    # Check metadata extraction
    assert any('nomor_hadis' in c.get('metadata', {}) for c in chunks)

@pytest.mark.asyncio
async def test_chunk_empty_text():
    """Test dengan text kosong"""
    chunker = HadisChunker()
    
    chunks = await chunker.chunk_text("", page_number=1)
    
    assert len(chunks) == 0
