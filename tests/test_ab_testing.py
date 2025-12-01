import pytest
from httpx import AsyncClient
from app.main import app
from app.services.llm_service import LLMService
import time

@pytest.mark.asyncio
async def test_prompt_variants():
    """A/B test different prompt variants"""
    
    test_query = "Apa itu wudhu?"
    test_chunks = [
        {
            "text": "Wudhu adalah bersuci dengan air untuk menghilangkan hadats kecil...",
            "page_number": 10,
            "metadata": {"perawi": "Bukhari"},
            "similarity": 0.85
        }
    ]
    
    llm = LLMService()
    
    # Variant A: Short prompt
    llm.prompt_variant = "short"
    start_a = time.time()
    answer_a = await llm.generate_response(test_query, test_chunks)
    time_a = time.time() - start_a
    
    # Variant B: Detailed prompt (original)
    llm.prompt_variant = "detailed"
    start_b = time.time()
    answer_b = await llm.generate_response(test_query, test_chunks)
    time_b = time.time() - start_b
    
    print(f"\n=== A/B Test Results ===")
    print(f"Variant A (Short):")
    print(f"  Time: {time_a:.2f}s")
    print(f"  Length: {len(answer_a)} chars")
    print(f"  Answer: {answer_a[:100]}...")
    print(f"\nVariant B (Detailed):")
    print(f"  Time: {time_b:.2f}s")
    print(f"  Length: {len(answer_b)} chars")
    print(f"  Answer: {answer_b[:100]}...")
    
    # Both should produce valid answers
    assert len(answer_a) > 10
    assert len(answer_b) > 10

@pytest.mark.asyncio
async def test_chunking_strategies():
    """Compare different chunking strategies"""
    from app.services.chunker import HadisChunker
    
    sample_text = "Hadis 1: Text... " * 100
    
    # Strategy A: Small chunks
    chunker_a = HadisChunker(chunk_size=500, overlap=100)
    chunks_a = await chunker_a.chunk_text(sample_text, 1)
    
    # Strategy B: Large chunks
    chunker_b = HadisChunker(chunk_size=1000, overlap=200)
    chunks_b = await chunker_b.chunk_text(sample_text, 1)
    
    print(f"\n=== Chunking Strategy Test ===")
    print(f"Strategy A (500 chars): {len(chunks_a)} chunks")
    print(f"Strategy B (1000 chars): {len(chunks_b)} chunks")
    
    assert len(chunks_a) >= len(chunks_b)
