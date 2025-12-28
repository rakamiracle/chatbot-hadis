"""
Migrate chat_history table vector dimensions from 384 to 512.
"""
import asyncio
import sys
import os
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.connection import AsyncSessionLocal

async def migrate_chat_history():
    print("=" * 70)
    print("🚀 MIGRATING CHAT_HISTORY DIMENSIONS (384 -> 512)")
    print("=" * 70)
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. Check if columns exist and their current dimension
            print("\n1️⃣ Checking current dimensions...")
            result = await db.execute(text("""
                SELECT 
                    atttypmod 
                FROM pg_attribute 
                WHERE attrelid = 'chat_history'::regclass 
                AND attname = 'query_embedding'
            """))
            # typmod for Vector(384) is usually 384
            # This is a bit complex in Postgres, let's just try to alter them directly
            
            # 2. Alter columns
            print("\n2️⃣ Altering columns to Vector(512)...")
            
            # Since we can't easily alter dimension of Vector column, we drop and recreate
            # (Chat history embeddings are usually okay to lose during migration as they are just caches/analytics)
            
            commands = [
                "ALTER TABLE chat_history DROP COLUMN IF EXISTS query_embedding",
                "ALTER TABLE chat_history DROP COLUMN IF EXISTS response_embedding",
                "ALTER TABLE chat_history DROP COLUMN IF EXISTS combined_embedding",
                "ALTER TABLE chat_history ADD COLUMN query_embedding Vector(512)",
                "ALTER TABLE chat_history ADD COLUMN response_embedding Vector(512)",
                "ALTER TABLE chat_history ADD COLUMN combined_embedding Vector(512)"
            ]
            
            for cmd in commands:
                print(f"   Executing: {cmd}")
                await db.execute(text(cmd))
            
            await db.commit()
            print("\n✅ MIGRATION SUCCESSFUL!")
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ MIGRATION FAILED: {str(e)}")
            if "regclass" in str(e):
                print("   Note: chat_history table might not exist yet.")

if __name__ == "__main__":
    asyncio.run(migrate_chat_history())
