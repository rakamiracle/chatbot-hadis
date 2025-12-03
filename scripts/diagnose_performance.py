"""
Script untuk diagnose performance bottleneck
Jalankan: python scripts/diagnose_performance.py
"""
import asyncio
import time
import os
from dotenv import load_dotenv

load_dotenv()

async def diagnose():
    print("🔍 Diagnosing Performance Issues...\n")
    
    # 1. Check Ollama
    print("1️⃣ Checking Ollama...")
    try:
        import ollama
        model = os.getenv("OLLAMA_MODEL", "mistral")
        print(f"   Model: {model}")
        
        start = time.time()
        response = ollama.generate(
            model=model,
            prompt="Test",
            options={"num_predict": 10}
        )
        elapsed = (time.time() - start) * 1000
        print(f"   ✓ Ollama response time: {elapsed:.0f}ms")
        
        if elapsed > 5000:
            print(f"   ⚠️  WARNING: Ollama is VERY slow ({elapsed:.0f}ms)")
            print(f"   Recommendation: Use smaller/faster model like 'mistral:7b-instruct-q4_0'")
    except Exception as e:
        print(f"   ❌ Ollama error: {e}")
    
    # 2. Check Embedding Model
    print("\n2️⃣ Checking Embedding Model...")
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        print(f"   Model: {model_name}")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"   Device: {device}")
        
        start = time.time()
        model = SentenceTransformer(model_name, device=device)
        load_time = (time.time() - start) * 1000
        print(f"   Model load time: {load_time:.0f}ms")
        
        start = time.time()
        _ = model.encode("test query", convert_to_numpy=True)
        embed_time = (time.time() - start) * 1000
        print(f"   ✓ Embedding time: {embed_time:.0f}ms")
        
        if embed_time > 500:
            print(f"   ⚠️  WARNING: Embedding is slow ({embed_time:.0f}ms)")
            if device == "cpu":
                print(f"   Recommendation: Use GPU if available")
    except Exception as e:
        print(f"   ❌ Embedding error: {e}")
    
    # 3. Check Database
    print("\n3️⃣ Checking Database...")
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
            engine = create_async_engine(database_url, echo=False)
            
            async with engine.begin() as conn:
                # Check chunk count
                start = time.time()
                result = await conn.execute(text("SELECT COUNT(*) FROM hadis_chunks"))
                count = result.scalar()
                query_time = (time.time() - start) * 1000
                print(f"   Total chunks: {count:,}")
                print(f"   ✓ Query time: {query_time:.0f}ms")
                
                # Check if HNSW index exists
                result = await conn.execute(text("""
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = 'hadis_chunks' 
                    AND indexname LIKE '%hnsw%'
                """))
                hnsw = result.fetchone()
                
                if hnsw:
                    print(f"   ✓ HNSW index: EXISTS")
                else:
                    print(f"   ⚠️  HNSW index: NOT FOUND")
                    print(f"   Recommendation: Run 'python scripts/add_vector_index.py'")
                
                # Test vector search
                if count > 0:
                    start = time.time()
                    result = await conn.execute(text("""
                        SELECT id FROM hadis_chunks 
                        ORDER BY embedding <=> '[0.1,0.2,0.3]'::vector 
                        LIMIT 5
                    """))
                    _ = result.fetchall()
                    search_time = (time.time() - start) * 1000
                    print(f"   Vector search time: {search_time:.0f}ms")
                    
                    if search_time > 500:
                        print(f"   ⚠️  WARNING: Vector search is slow ({search_time:.0f}ms)")
                        print(f"   Recommendation: Add HNSW index")
            
            await engine.dispose()
    except Exception as e:
        print(f"   ❌ Database error: {e}")
    
    # 4. Summary
    print("\n" + "="*60)
    print("📊 DIAGNOSIS SUMMARY")
    print("="*60)
    print("\nIf you see any ⚠️  warnings above, follow the recommendations.")
    print("\nCommon fixes:")
    print("1. Add HNSW index: python scripts/add_vector_index.py")
    print("2. Use faster Ollama model: ollama pull mistral:7b-instruct-q4_0")
    print("3. Enable GPU for embeddings (if available)")
    print("4. Reduce num_predict in LLM options (currently 200)")

if __name__ == "__main__":
    asyncio.run(diagnose())
