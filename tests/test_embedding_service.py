import pytest
from app.services.embedding_service import EmbeddingService

@pytest.fixture
def embedding_service():
    return EmbeddingService()

@pytest.mark.asyncio
async def test_generate_single_embedding(embedding_service):
    """Test generate single embedding"""
    text = "Ini adalah hadis tentang shalat"
    
    embedding = await embedding_service.generate_embedding(text)
    
    assert embedding is not None
    assert isinstance(embedding, list)
    assert len(embedding) == 384  # Model dimension
    assert all(isinstance(x, float) for x in embedding)

@pytest.mark.asyncio
async def test_generate_batch_embeddings(embedding_service):
    """Test batch embedding generation"""
    texts = [
        "Hadis tentang shalat",
        "Hadis tentang puasa",
        "Hadis tentang zakat"
    ]
    
    embeddings = await embedding_service.generate_embeddings_batch(texts)
    
    assert len(embeddings) == len(texts)
    assert all(len(emb) == 384 for emb in embeddings)

@pytest.mark.asyncio
async def test_embedding_consistency(embedding_service):
    """Test konsistensi embedding untuk text sama"""
    text = "Hadis tentang shalat"
    
    emb1 = await embedding_service.generate_embedding(text)
    emb2 = await embedding_service.generate_embedding(text)
    
    # Should be very similar (allowing small float differences)
    import numpy as np
    similarity = np.dot(emb1, emb2)
    
    assert similarity > 0.99  # Very high similarity

