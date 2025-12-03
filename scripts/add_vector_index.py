"""
Script untuk menambahkan HNSW index pada embedding column
HNSW (Hierarchical Navigable Small World) jauh lebih cepat dari brute-force search

Jalankan: python scripts/add_vector_index.py
"""
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def add_hnsw_index():
    """Add HNSW index untuk mempercepat vector similarity search"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in .env file")
        return
    
    # Convert to async URL
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Create engine
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.begin() as conn:
        try:
            # Check if index already exists
            check_query = text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'hadis_chunks' 
                AND indexname = 'hadis_chunks_embedding_hnsw_idx'
            """)
            result = await conn.execute(check_query)
            existing = result.fetchone()
            
            if existing:
                print("✓ HNSW index already exists")
                return
            
            print("Creating HNSW index on embedding column...")
            print("This may take a few minutes depending on dataset size...")
            
            # Create HNSW index
            # m = 16: number of connections per layer (higher = better recall, slower build)
            # ef_construction = 64: size of dynamic candidate list (higher = better quality, slower build)
            create_index_query = text("""
                CREATE INDEX hadis_chunks_embedding_hnsw_idx 
                ON hadis_chunks 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """)
            
            await conn.execute(create_index_query)
            print("✓ HNSW index created successfully!")
            print("  This will make vector searches 5-10x faster on large datasets")
            
            # Also add index on document_id for faster filtering
            print("\nAdding index on document_id...")
            doc_index_query = text("""
                CREATE INDEX IF NOT EXISTS hadis_chunks_document_id_idx 
                ON hadis_chunks(document_id);
            """)
            await conn.execute(doc_index_query)
            print("✓ Document ID index created")
            
            print("\n🎉 All indexes created successfully!")
            
        except Exception as e:
            print(f"❌ Error creating index: {e}")
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_hnsw_index())

