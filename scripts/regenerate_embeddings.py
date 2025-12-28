"""
Script untuk regenerate embeddings setelah ganti model embedding.
WAJIB dijalankan setelah update EMBEDDING_MODEL di .env

Usage:
    python scripts/regenerate_embeddings.py
"""

import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.connection import AsyncSessionLocal
from app.models.chunk import HadisChunk
from app.services.embedding_service import EmbeddingService
from app.utils.logger import logger

async def get_total_chunks(db: AsyncSession) -> int:
    """Get total number of chunks in database"""
    result = await db.execute(select(func.count()).select_from(HadisChunk))
    return result.scalar()

async def regenerate_embeddings(batch_size: int = 50, skip_confirmation: bool = False):
    """
    Regenerate all embeddings in database
    
    Args:
        batch_size: Number of chunks to process before committing
        skip_confirmation: Skip user confirmation prompt
    """
    print("=" * 70)
    print("🔄 REGENERATE EMBEDDINGS SCRIPT")
    print("=" * 70)
    
    # Initialize embedding service
    print("\n📦 Loading embedding model...")
    embed_service = EmbeddingService()
    print("✅ Model loaded successfully!\n")
    
    async with AsyncSessionLocal() as db:
        # Get total count
        total_chunks = await get_total_chunks(db)
        
        if total_chunks == 0:
            print("⚠️  No chunks found in database. Nothing to regenerate.")
            return
        
        print(f"📊 Found {total_chunks:,} chunks in database")
        print(f"⚙️  Batch size: {batch_size}")
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Confirmation
        if not skip_confirmation:
            print("\n" + "=" * 70)
            print("⚠️  WARNING: This will regenerate ALL embeddings in the database!")
            print("=" * 70)
            confirm = input("\nAre you sure you want to continue? (yes/no): ")
            if confirm.lower() not in ['yes', 'y']:
                print("❌ Operation cancelled.")
                return
        
        print("\n" + "=" * 70)
        print("🚀 Starting regeneration process...")
        print("=" * 70 + "\n")
        
        start_time = datetime.now()
        processed = 0
        errors = 0
        
        # Fetch all chunks (batch processing for memory efficiency)
        offset = 0
        
        while offset < total_chunks:
            # Fetch batch of chunks
            result = await db.execute(
                select(HadisChunk)
                .offset(offset)
                .limit(batch_size)
            )
            chunks = result.scalars().all()
            
            if not chunks:
                break
            
            # Process each chunk in the batch
            for chunk in chunks:
                try:
                    # Generate new embedding
                    new_embedding = await embed_service.generate_embedding(chunk.chunk_text)
                    chunk.embedding = new_embedding
                    processed += 1
                    
                except Exception as e:
                    errors += 1
                    logger.error(f"Error processing chunk {chunk.chunk_id}: {str(e)}")
                    print(f"❌ Error on chunk {chunk.chunk_id}: {str(e)}")
                    continue
            
            # Commit batch
            try:
                await db.commit()
                
                # Calculate progress
                percentage = (processed / total_chunks) * 100
                elapsed = (datetime.now() - start_time).total_seconds()
                chunks_per_sec = processed / elapsed if elapsed > 0 else 0
                eta_seconds = (total_chunks - processed) / chunks_per_sec if chunks_per_sec > 0 else 0
                eta_minutes = eta_seconds / 60
                
                # Progress bar
                bar_length = 40
                filled_length = int(bar_length * processed / total_chunks)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                
                print(f"\r[{bar}] {percentage:.1f}% | {processed:,}/{total_chunks:,} chunks | "
                      f"{chunks_per_sec:.1f} chunks/s | ETA: {eta_minutes:.1f}m", end='')
                
            except Exception as e:
                errors += 1
                logger.error(f"Error committing batch at offset {offset}: {str(e)}")
                print(f"\n❌ Error committing batch: {str(e)}")
                await db.rollback()
            
            offset += batch_size
        
        # Final stats
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n\n" + "=" * 70)
        print("✅ REGENERATION COMPLETE!")
        print("=" * 70)
        print(f"📊 Total chunks: {total_chunks:,}")
        print(f"✅ Successfully processed: {processed:,}")
        print(f"❌ Errors: {errors}")
        print(f"⏱️  Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print(f"⚡ Average speed: {processed/duration:.2f} chunks/second")
        print(f"📅 Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        if errors > 0:
            print(f"\n⚠️  {errors} chunks failed. Check logs for details.")
        else:
            print("\n🎉 All embeddings regenerated successfully!")

async def test_embedding_dimension():
    """Test to verify new embedding dimension"""
    print("\n" + "=" * 70)
    print("🧪 Testing new embedding dimension...")
    print("=" * 70)
    
    embed_service = EmbeddingService()
    test_text = "Test hadis untuk verifikasi dimensi embedding"
    
    embedding = await embed_service.generate_embedding(test_text)
    dimension = len(embedding)
    
    print(f"✅ New embedding dimension: {dimension}")
    print(f"📝 Test text: '{test_text[:50]}...'")
    print(f"📊 Sample embedding (first 5 values): {embedding[:5]}")
    
    # Check against common dimensions
    if dimension == 384:
        print("ℹ️  Dimension 384 = paraphrase-multilingual-MiniLM-L12-v2")
    elif dimension == 512:
        print("ℹ️  Dimension 512 = distiluse-base-multilingual-cased-v2")
    elif dimension == 768:
        print("ℹ️  Dimension 768 = BERT-based models")
    
    return dimension

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Regenerate embeddings after changing EMBEDDING_MODEL'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of chunks to process per batch (default: 50)'
    )
    parser.add_argument(
        '--skip-confirmation',
        action='store_true',
        help='Skip confirmation prompt (use with caution!)'
    )
    parser.add_argument(
        '--test-only',
        action='store_true',
        help='Only test embedding dimension without regenerating'
    )
    
    args = parser.parse_args()
    
    try:
        # Test embedding first
        dimension = await test_embedding_dimension()
        
        if args.test_only:
            print("\n✅ Test complete. Use without --test-only to regenerate embeddings.")
            return
        
        # Confirm dimension
        print("\n" + "=" * 70)
        print(f"⚠️  This will regenerate all embeddings with dimension: {dimension}")
        print("=" * 70)
        
        # Run regeneration
        await regenerate_embeddings(
            batch_size=args.batch_size,
            skip_confirmation=args.skip_confirmation
        )
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\n❌ FATAL ERROR: {str(e)}")
        print("Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
