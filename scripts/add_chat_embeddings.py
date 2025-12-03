"""
Database migration script to add vector embeddings to chat_history table

This script:
1. Adds query_embedding column (VECTOR(384)) for user query embeddings
2. Adds response_embedding column (VECTOR(384)) for bot response embeddings
3. Adds combined_embedding column (VECTOR(384)) for full conversation embeddings
4. Creates HNSW indexes on all three embedding columns for fast similarity search

Jalankan: python scripts/add_chat_embeddings.py
"""
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def add_chat_embedding_columns():
    """Add embedding columns to chat_history table"""
    
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
            print("ADDING CHAT HISTORY VECTOR EMBEDDINGS")
            print("=" * 70)
            
            # Check if columns already exist
            print("\n1. Checking existing schema...")
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'chat_history' 
                AND column_name IN ('query_embedding', 'response_embedding', 'combined_embedding')
            """)
            result = await conn.execute(check_query)
            existing_columns = [row[0] for row in result.fetchall()]
            
            columns_to_add = []
            if 'query_embedding' not in existing_columns:
                columns_to_add.append('query_embedding')
            if 'response_embedding' not in existing_columns:
                columns_to_add.append('response_embedding')
            if 'combined_embedding' not in existing_columns:
                columns_to_add.append('combined_embedding')
            
            if not columns_to_add:
                print("   ✓ All embedding columns already exist")
            else:
                # Add query_embedding column
                if 'query_embedding' in columns_to_add:
                    print("\n2. Adding query_embedding column...")
                    await conn.execute(text("""
                        ALTER TABLE chat_history 
                        ADD COLUMN query_embedding vector(384)
                    """))
                    print("   ✓ query_embedding column added")
                
                # Add response_embedding column
                if 'response_embedding' in columns_to_add:
                    print("\n3. Adding response_embedding column...")
                    await conn.execute(text("""
                        ALTER TABLE chat_history 
                        ADD COLUMN response_embedding vector(384)
                    """))
                    print("   ✓ response_embedding column added")
                
                # Add combined_embedding column
                if 'combined_embedding' in columns_to_add:
                    print("\n4. Adding combined_embedding column...")
                    await conn.execute(text("""
                        ALTER TABLE chat_history 
                        ADD COLUMN combined_embedding vector(384)
                    """))
                    print("   ✓ combined_embedding column added")
            
            # Check and create HNSW indexes
            print("\n5. Checking for HNSW indexes...")
            
            indexes_to_create = []
            index_names = [
                'chat_history_query_embedding_hnsw_idx',
                'chat_history_response_embedding_hnsw_idx',
                'chat_history_combined_embedding_hnsw_idx'
            ]
            
            for index_name in index_names:
                check_index_query = text(f"""
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = 'chat_history' 
                    AND indexname = '{index_name}'
                """)
                result = await conn.execute(check_index_query)
                if not result.fetchone():
                    indexes_to_create.append(index_name)
            
            if not indexes_to_create:
                print("   ✓ All HNSW indexes already exist")
            else:
                print(f"\n6. Creating {len(indexes_to_create)} HNSW indexes...")
                print("   This may take a few minutes if you have many chat records...")
                
                # Create HNSW index for query_embedding
                if 'chat_history_query_embedding_hnsw_idx' in indexes_to_create:
                    print("   Creating index on query_embedding...")
                    await conn.execute(text("""
                        CREATE INDEX chat_history_query_embedding_hnsw_idx 
                        ON chat_history 
                        USING hnsw (query_embedding vector_cosine_ops)
                        WITH (m = 16, ef_construction = 64);
                    """))
                    print("   ✓ query_embedding index created")
                
                # Create HNSW index for response_embedding
                if 'chat_history_response_embedding_hnsw_idx' in indexes_to_create:
                    print("   Creating index on response_embedding...")
                    await conn.execute(text("""
                        CREATE INDEX chat_history_response_embedding_hnsw_idx 
                        ON chat_history 
                        USING hnsw (response_embedding vector_cosine_ops)
                        WITH (m = 16, ef_construction = 64);
                    """))
                    print("   ✓ response_embedding index created")
                
                # Create HNSW index for combined_embedding
                if 'chat_history_combined_embedding_hnsw_idx' in indexes_to_create:
                    print("   Creating index on combined_embedding...")
                    await conn.execute(text("""
                        CREATE INDEX chat_history_combined_embedding_hnsw_idx 
                        ON chat_history 
                        USING hnsw (combined_embedding vector_cosine_ops)
                        WITH (m = 16, ef_construction = 64);
                    """))
                    print("   ✓ combined_embedding index created")
            
            print("\n" + "=" * 70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print("\nNext steps:")
            print("1. Run backfill script: python scripts/backfill_chat_embeddings.py")
            print("2. New chats will automatically get embeddings")
            print()
            
        except Exception as e:
            print(f"\n❌ Error during migration: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_chat_embedding_columns())
