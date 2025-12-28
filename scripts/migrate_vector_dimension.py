"""
Migration script: Update embedding dimension from 384 to 512
Run this BEFORE regenerating embeddings

WARNING: This will DROP all existing embeddings!

Usage:
    python scripts/migrate_vector_dimension.py
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.connection import AsyncSessionLocal
from sqlalchemy import text
from app.utils.logger import logger

async def migrate_vector_dimension():
    """
    Migrate vector dimension from 384 to 512
    This will DROP existing embeddings column and recreate it
    """
    print("=" * 70)
    print("🔄 MIGRATE VECTOR DIMENSION: 384 → 512")
    print("=" * 70)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Warning
    print("⚠️" * 35)
    print("⚠️  WARNING: This will DELETE all existing embeddings!")
    print("⚠️  Make sure you have database backup before proceeding!")
    print("⚠️" * 35)
    print()
    
    confirm = input("Type 'YES' to confirm (case-sensitive): ")
    if confirm != 'YES':
        print("❌ Migration cancelled.")
        return
    
    print("\n" + "=" * 70)
    print("🚀 Starting migration...")
    print("=" * 70 + "\n")
    
    try:
        async with AsyncSessionLocal() as db:
            # Step 1: Drop existing embedding columns in BOTH tables
            print("📌 Step 1/5: Dropping old embedding columns (384 dimensions)...")
            print("  - hadis_chunks table...")
            await db.execute(text("""
                ALTER TABLE hadis_chunks 
                DROP COLUMN IF EXISTS embedding;
            """))
            print("  - hadis_documents table...")
            await db.execute(text("""
                ALTER TABLE hadis_documents 
                DROP COLUMN IF EXISTS embedding;
            """))
            await db.commit()
            print("✅ Old columns dropped\n")
            
            # Step 2: Add new embedding column to hadis_chunks (512 dimensions)
            print("📌 Step 2/5: Creating new embedding column for chunks (512 dimensions)...")
            await db.execute(text("""
                ALTER TABLE hadis_chunks 
                ADD COLUMN embedding vector(512);
            """))
            await db.commit()
            print("✅ Chunks column created\n")
            
            # Step 3: Add new embedding column to hadis_documents (512 dimensions)
            print("📌 Step 3/5: Creating new embedding column for documents (512 dimensions)...")
            await db.execute(text("""
                ALTER TABLE hadis_documents 
                ADD COLUMN embedding vector(512);
            """))
            await db.commit()
            print("✅ Documents column created\n")
            
            # Step 4: Create index for chunks
            print("📌 Step 4/5: Creating vector index for chunks...")
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS hadis_chunks_embedding_idx 
                ON hadis_chunks 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """))
            await db.commit()
            print("✅ Chunks index created\n")
            
            # Step 5: Create index for documents
            print("📌 Step 5/5: Creating vector index for documents...")
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS hadis_documents_embedding_idx 
                ON hadis_documents 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """))
            await db.commit()
            print("✅ Documents index created\n")
            
            # Verify
            print("📊 Verifying schema...")
            result = await db.execute(text("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns 
                WHERE table_name = 'hadis_chunks' 
                AND column_name = 'embedding';
            """))
            row = result.fetchone()
            
            if row:
                print(f"✅ Verified: {row[0]} | Type: {row[1]} | UDT: {row[2]}")
            else:
                print("⚠️  Could not verify column (but probably OK)")
            
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 70)
        print("📝 Next steps:")
        print("   1. Restart your application")
        print("   2. Run: python scripts/regenerate_embeddings.py")
        print("=" * 70)
        print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        print(f"\n❌ MIGRATION FAILED: {str(e)}")
        print("\nPossible solutions:")
        print("1. Check database connection")
        print("2. Ensure pgvector extension is installed")
        print("3. Check database user permissions")
        print("4. Restore from backup if needed")
        sys.exit(1)

async def check_current_dimension():
    """Check current vector dimension"""
    print("\n" + "=" * 70)
    print("🔍 Checking current embedding dimension...")
    print("=" * 70)
    
    try:
        async with AsyncSessionLocal() as db:
            # Check if column exists
            result = await db.execute(text("""
                SELECT column_name, udt_name
                FROM information_schema.columns 
                WHERE table_name = 'hadis_chunks' 
                AND column_name = 'embedding';
            """))
            row = result.fetchone()
            
            if not row:
                print("⚠️  No embedding column found")
                return None
            
            print(f"✅ Found: {row[0]} | Type: {row[1]}")
            
            # Try to get actual dimension from a sample
            count_result = await db.execute(text("""
                SELECT COUNT(*) FROM hadis_chunks WHERE embedding IS NOT NULL;
            """))
            count = count_result.scalar()
            
            if count > 0:
                sample_result = await db.execute(text("""
                    SELECT array_length(embedding::real[], 1) as dim
                    FROM hadis_chunks 
                    WHERE embedding IS NOT NULL 
                    LIMIT 1;
                """))
                dim = sample_result.scalar()
                print(f"📊 Current dimension: {dim}")
                print(f"📊 Total chunks with embeddings: {count:,}")
                return dim
            else:
                print("📊 No embeddings found in database (empty)")
                return 0
                
    except Exception as e:
        logger.error(f"Check failed: {str(e)}", exc_info=True)
        print(f"❌ Could not check dimension: {str(e)}")
        return None

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrate vector dimension from 384 to 512'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check current dimension without migrating'
    )
    
    args = parser.parse_args()
    
    try:
        # Always check first
        current_dim = await check_current_dimension()
        
        if args.check_only:
            print("\n✅ Check complete.")
            return
        
        if current_dim == 512:
            print("\n✅ Already using 512 dimensions. No migration needed!")
            print("   You can now run: python scripts/regenerate_embeddings.py")
            return
        
        if current_dim == 384:
            print(f"\n⚠️  Current dimension: {current_dim}")
            print("   Migration needed to 512 dimensions")
        
        # Run migration
        await migrate_vector_dimension()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\n❌ FATAL ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
