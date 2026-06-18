"""
Diagnostic script untuk debug vector search issue
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.connection import AsyncSessionLocal
from app.services.embedding_service import EmbeddingService
from app.models.chunk import HadisChunk
from sqlalchemy import select, text
import numpy as np

async def diagnose():
    print("=" * 70)
    print("🔍 VECTOR SEARCH DIAGNOSTIC")
    print("=" * 70)
    
    # Test query
    test_query = "jelaskan tentang sholat"
    print(f"\n📝 Test Query: '{test_query}'")
    
    # 1. Generate query embedding
    print("\n1️⃣  Generating query embedding...")
    embed_service = EmbeddingService()
    query_emb = await embed_service.generate_embedding(test_query)
    print(f"   ✅ Query embedding: {len(query_emb)} dimensions")
    print(f"   Sample values: {query_emb[:5]}")
    
    async with AsyncSessionLocal() as db:
        # 2. Check database chunks
        print("\n2️⃣  Checking database chunks...")
        result = await db.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(embedding) as with_emb,
                COUNT(*) - COUNT(embedding) as missing
            FROM hadis_chunks
        """))
        row = result.fetchone()
        print(f"   Total chunks: {row[0]:,}")
        print(f"   With embeddings: {row[1]:,}")
        print(f"   Missing: {row[2]:,}")
        
        if row[2] > 0:
            print(f"   ⚠️  WARNING: {row[2]:,} chunks missing embeddings!")
        
        # 3. Check embedding dimension
        print("\n3️⃣  Checking embedding dimensions...")
        result = await db.execute(text("""
            SELECT array_length(embedding::real[], 1) as dim
            FROM hadis_chunks 
            WHERE embedding IS NOT NULL
            LIMIT 1
        """))
        dim = result.scalar()
        print(f"   Database embedding dimension: {dim}")
        
        if dim != len(query_emb):
            print(f"   ❌ MISMATCH! Query:{len(query_emb)} vs DB:{dim}")
            return
        
        # 4. Raw vector search (NO threshold, NO filter)
        print("\n4️⃣  Performing RAW vector search (no filters)...")
        result = await db.execute(
            select(
                HadisChunk.id,
                HadisChunk.chunk_text,
                (1 - HadisChunk.embedding.cosine_distance(query_emb)).label('similarity')
            )
            .where(HadisChunk.embedding.isnot(None))
            .order_by(HadisChunk.embedding.cosine_distance(query_emb))
            .limit(10)
        )
        
        rows = result.all()
        
        if not rows:
            print("   ❌ NO RESULTS from raw search!")
            print("   This suggests a fundamental problem with vector search.")
            return
        
        print(f"   ✅ Found {len(rows)} results")
        print("\n   Top 10 Results:")
        print("   " + "-" * 66)
        
        for i, row in enumerate(rows, 1):
            sim = float(row.similarity)
            preview = row.chunk_text[:60].replace('\n', ' ')
            status = "✅" if sim >= 0.3 else "❌"
            print(f"   {i}. {status} Sim: {sim:.4f} | ID:{row.id} | {preview}...")
        
        # 5. Analyze similarity scores
        print("\n5️⃣  Similarity Score Analysis:")
        similarities = [float(r.similarity) for r in rows]
        print(f"   Max: {max(similarities):.4f}")
        print(f"   Min: {min(similarities):.4f}")
        print(f"   Avg: {np.mean(similarities):.4f}")
        print(f"   Median: {np.median(similarities):.4f}")
        
        # Check threshold
        above_03 = sum(1 for s in similarities if s >= 0.3)
        above_05 = sum(1 for s in similarities if s >= 0.5)
        above_065 = sum(1 for s in similarities if s >= 0.65)
        
        print(f"\n   Results passing threshold:")
        print(f"   ≥ 0.3:  {above_03}/10")
        print(f"   ≥ 0.5:  {above_05}/10")
        print(f"   ≥ 0.65: {above_065}/10")
        
        if max(similarities) < 0.3:
            print(f"\n   ⚠️  PROBLEM FOUND!")
            print(f"   Max similarity ({max(similarities):.4f}) < threshold (0.3)")
            print(f"   Embeddings might be incompatible or corrupted!")
            print(f"\n   🔧 Suggestions:")
            print(f"   1. Re-run complete_missing_embeddings.py")
            print(f"   2. Or regenerate ALL embeddings from scratch")
        elif above_03 > 0:
            print(f"\n   ✅ {above_03} results should pass threshold 0.3")
            print(f"   Check if vector_search.py is using correct threshold.")
        
        # 6. Test with actual VectorSearch service
        print("\n6️⃣  Testing with VectorSearch service...")
        from app.services.vector_search import VectorSearch
        search_service = VectorSearch()
        
        results = await search_service.search_similar(
            query_embedding=query_emb,
            query_text=test_query,
            db=db,
            top_k=5
        )
        
        if not results:
            print("   ❌ VectorSearch returned 0 results!")
            print("   Check VectorSearch logic and threshold.")
        else:
            print(f"   ✅ VectorSearch returned {len(results)} results")
            for i, r in enumerate(results, 1):
                print(f"   {i}. Score: {r.get('final_score', 0):.4f} | {r['text'][:60]}...")
        
        print("\n" + "=" * 70)
        print("✅ Diagnostic Complete")
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(diagnose())
