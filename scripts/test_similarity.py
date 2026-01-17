import asyncio
from sqlalchemy import select, text
from app.database.connection import get_db
from app.services.embedding_service import EmbeddingService
from app.models.chunk import HadisChunk

async def test_similarity():
    embed_service = EmbeddingService()
    
    # Query test
    query = "Apa itu wudhu?"
    print(f"🔍 Testing similarity search")
    print(f"Query: {query}")
    print("="*80)
    
    # Generate embedding untuk query
    print("\n1️⃣ Generate query embedding...")
    query_emb = await embed_service.generate_embedding(query)
    print(f"   ✓ Query vector: {len(query_emb)} dimensions")
    print(f"   Sample: {query_emb[:5]}")
    
    # Search similar vectors
    print("\n2️⃣ Searching similar vectors in database...")
    
    async for db in get_db():
        # Manual similarity search
        result = await db.execute(text("""
            SELECT 
                id,
                chunk_text,
                page_number,
                chunk_metadata->>'kitab' as kitab,
                1 - (embedding <=> :query_emb::vector) as similarity
            FROM hadis_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :query_emb::vector
            LIMIT 5
        """), {"query_emb": query_emb})
        
        rows = result.fetchall()
        
        print(f"\n   Found {len(rows)} results:\n")
        
        for i, row in enumerate(rows, 1):
            print(f"   [{i}] Similarity: {row.similarity:.4f}")
            print(f"       Kitab: {row.kitab}")
            print(f"       Page: {row.page_number}")
            print(f"       Text: {row.chunk_text[:150]}...")
            print()
        
        break
    
    print("="*80)
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_similarity())