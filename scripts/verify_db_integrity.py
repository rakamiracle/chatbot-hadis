
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def run():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not found in .env")
        return
    
    # Handle asyncpg format
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = await asyncpg.connect(url)
        
        print("-" * 50)
        print("DATABASE INTEGRITY CHECK")
        print("-" * 50)
        
        # 1. Check counts
        chunks_count = await conn.fetchval("SELECT COUNT(*) FROM hadis_chunks")
        docs_count = await conn.fetchval("SELECT COUNT(*) FROM hadis_documents")
        
        print(f"Chunks count: {chunks_count:,}")
        print(f"Documents count: {docs_count:,}")
        
        # 2. Check join
        join_count = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM hadis_chunks c 
            JOIN hadis_documents d ON c.document_id = d.id
        """)
        print(f"Joined count: {join_count:,}")
        
        if join_count == 0 and chunks_count > 0:
            print("❌ ERROR: Join returned 0 rows! document_id mismatch?")
            
            # Check sample IDs
            chunk_doc_ids = await conn.fetch("SELECT DISTINCT document_id FROM hadis_chunks LIMIT 5")
            print(f"Sample document_ids in chunks: {[r['document_id'] for r in chunk_doc_ids]}")
            
            doc_ids = await conn.fetch("SELECT id FROM hadis_documents LIMIT 5")
            print(f"Sample ids in documents: {[r['id'] for r in doc_ids]}")
        
        # 3. Check embeddings
        emb_count = await conn.fetchval("SELECT COUNT(*) FROM hadis_chunks WHERE embedding IS NOT NULL")
        print(f"Chunks with embeddings: {emb_count:,}")
        
        if emb_count > 0:
            dim = await conn.fetchval("SELECT array_length(embedding::real[], 1) FROM hadis_chunks WHERE embedding IS NOT NULL LIMIT 1")
            print(f"Embedding dimension: {dim}")
            
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())
