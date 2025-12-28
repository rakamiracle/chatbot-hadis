"""
Complete missing embeddings - Only regenerate chunks without embeddings
Much faster than regenerating ALL chunks

Usage:
    python scripts/complete_missing_embeddings.py
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.connection import AsyncSessionLocal
from app.models.chunk import HadisChunk
from app.services.embedding_service import EmbeddingService
from app.utils.logger import logger
from sqlalchemy import select

async def complete_missing_embeddings(batch_size: int = 50):
    """
    Generate embeddings ONLY for chunks that don't have them
    """
    print("=" * 70)
    print("🔄 COMPLETE MISSING EMBEDDINGS")
    print("=" * 70)
    
    # Initialize embedding service
    print("\n📦 Loading embedding model...")
    embed_service = EmbeddingService()
    print("✅ Model loaded!\n")
    
    async with AsyncSessionLocal() as db:
        # Count missing embeddings
        result = await db.execute(
            select(HadisChunk)
            .where(HadisChunk.embedding == None)
        )
        missing_chunks = result.scalars().all()
        total_missing = len(missing_chunks)
        
        if total_missing == 0:
            print("✅ All chunks already have embeddings!")
            return
        
        print(f"📊 Found {total_missing:,} chunks WITHOUT embeddings")
        print(f"⚙️  Batch size: {batch_size}")
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        confirm = input("\nProceed to generate embeddings? (yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("❌ Cancelled.")
            return
        
        print("\n" + "=" * 70)
        print("🚀 Generating embeddings...")
        print("=" * 70 + "\n")
        
        start_time = datetime.now()
        processed = 0
        errors = 0
        
        # Process in batches
        for i in range(0, total_missing, batch_size):
            batch = missing_chunks[i:i + batch_size]
            
            for chunk in batch:
                try:
                    # Generate embedding
                    new_embedding = await embed_service.generate_embedding(chunk.chunk_text)
                    chunk.embedding = new_embedding
                    processed += 1
                    
                except Exception as e:
                    errors += 1
                    logger.error(f"Error processing chunk {chunk.id}: {str(e)}")
                    print(f"❌ Error on chunk {chunk.id}")
                    continue
            
            # Commit batch
            try:
                await db.commit()
                
                # Progress
                percentage = (processed / total_missing) * 100
                elapsed = (datetime.now() - start_time).total_seconds()
                speed = processed / elapsed if elapsed > 0 else 0
                eta = (total_missing - processed) / speed if speed > 0 else 0
                
                bar_length = 40
                filled = int(bar_length * processed / total_missing)
                bar = '█' * filled + '-' * (bar_length - filled)
                
                print(f"\r[{bar}] {percentage:.1f}% | {processed:,}/{total_missing:,} | "
                      f"{speed:.1f}/s | ETA: {eta/60:.1f}m", end='')
                
            except Exception as e:
                errors += 1
                logger.error(f"Error committing batch: {str(e)}")
                await db.rollback()
        
        # Final stats
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n\n" + "=" * 70)
        print("✅ COMPLETE!")
        print("=" * 70)
        print(f"📊 Total processed: {processed:,}")
        print(f"❌ Errors: {errors}")
        print(f"⏱️  Duration: {duration:.2f}s ({duration/60:.2f}m)")
        print(f"⚡ Speed: {processed/duration:.2f} chunks/s")
        print("=" * 70)
        
        if errors == 0:
            print("\n🎉 All missing embeddings generated successfully!")
        else:
            print(f"\n⚠️  {errors} chunks failed. Check logs.")

async def main():
    try:
        await complete_missing_embeddings(batch_size=50)
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\n❌ FATAL ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
