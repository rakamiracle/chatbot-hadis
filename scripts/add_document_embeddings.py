"""
Database migration script to add vector embeddings to hadis_documents table

This script:
1. Adds summary_text column (TEXT) to store document summary
2. Adds embedding column (VECTOR(384)) for document-level embeddings
3. Creates HNSW index on embedding column for fast similarity search

Jalankan: python scripts/add_document_embeddings.py
"""
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def add_document_embedding_columns():
    """Add embedding and summary_text columns to hadis_documents table"""
    
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
            print("=" * 70)
            print("ADDING DOCUMENT-LEVEL VECTOR EMBEDDINGS")
            print("=" * 70)
            
            # Check if columns already exist
            print("\n1. Checking existing schema...")
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'hadis_documents' 
                AND column_name IN ('summary_text', 'embedding')
            """)
            result = await conn.execute(check_query)
            existing_columns = [row[0] for row in result.fetchall()]
            
            if 'summary_text' in existing_columns and 'embedding' in existing_columns:
                print("   ✓ Columns already exist")
            else:
                # Add summary_text column
                if 'summary_text' not in existing_columns:
                    print("\n2. Adding summary_text column...")
                    await conn.execute(text("""
                        ALTER TABLE hadis_documents 
                        ADD COLUMN summary_text TEXT
                    """))
                    print("   ✓ summary_text column added")
                else:
                    print("\n2. summary_text column already exists")
                
                # Add embedding column
                if 'embedding' not in existing_columns:
                    print("\n3. Adding embedding column (Vector 384)...")
                    await conn.execute(text("""
                        ALTER TABLE hadis_documents 
                        ADD COLUMN embedding vector(384)
                    """))
                    print("   ✓ embedding column added")
                else:
                    print("\n3. embedding column already exists")
            
            # Check if HNSW index exists
            print("\n4. Checking for HNSW index...")
            check_index_query = text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'hadis_documents' 
                AND indexname = 'hadis_documents_embedding_hnsw_idx'
            """)
            result = await conn.execute(check_index_query)
            index_exists = result.fetchone()
            
            if index_exists:
                print("   ✓ HNSW index already exists")
            else:
                print("\n5. Creating HNSW index on embedding column...")
                print("   This may take a few minutes if you have many documents...")
                
                # Create HNSW index for fast similarity search
                create_index_query = text("""
                    CREATE INDEX hadis_documents_embedding_hnsw_idx 
                    ON hadis_documents 
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                """)
                
                await conn.execute(create_index_query)
                print("   ✓ HNSW index created successfully!")
                print("   This will make document-level vector searches 5-10x faster")
            
            print("\n" + "=" * 70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print("\nNext steps:")
            print("1. Run backfill script: python scripts/backfill_document_embeddings.py")
            print("2. Upload new documents will automatically get embeddings")
            print()
            
        except Exception as e:
            print(f"\n❌ Error during migration: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_document_embedding_columns())
