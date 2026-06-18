"""
Backfill document embeddings for existing documents

This script generates embeddings for documents that don't have them yet.
It creates a summary from the first 5 chunks and generates an embedding.

Jalankan: python scripts/backfill_document_embeddings.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, and_
from app.database.connection import get_db
from app.models.document import HadisDocument
from app.models.chunk import HadisChunk
from app.services.embedding_service import EmbeddingService

async def backfill_document_embeddings():
    """Backfill embeddings for existing documents"""
    
    embed_service = EmbeddingService()
    
    async for db in get_db():
        try:
            print("=" * 70)
            print("BACKFILLING DOCUMENT EMBEDDINGS")
            print("=" * 70)
            
            # Find documents without embeddings
            print("\n1. Finding documents without embeddings...")
            result = await db.execute(
                select(HadisDocument)
                .where(HadisDocument.embedding.is_(None))
                .order_by(HadisDocument.id)
            )
            docs_without_embeddings = result.scalars().all()
            
            if len(docs_without_embeddings) == 0:
                print("   ✓ All documents already have embeddings!")
                print("\n" + "=" * 70)
                return
            
            print(f"   Found {len(docs_without_embeddings)} documents without embeddings")
            
            # Process each document
            processed = 0
            failed = 0
            
            for i, doc in enumerate(docs_without_embeddings, 1):
                try:
                    print(f"\n{i}/{len(docs_without_embeddings)}. Processing: {doc.kitab_name or doc.filename}")
                    print(f"   Document ID: {doc.id}")
                    
                    # Get first 5 chunks for this document
                    chunk_result = await db.execute(
                        select(HadisChunk)
                        .where(HadisChunk.document_id == doc.id)
                        .order_by(HadisChunk.chunk_index)
                        .limit(5)
                    )
                    chunks = chunk_result.scalars().all()
                    
                    if len(chunks) == 0:
                        print("   ⚠️  No chunks found, skipping...")
                        failed += 1
                        continue
                    
                    # Create summary from chunks
                    summary_text = " ".join([chunk.chunk_text for chunk in chunks])
                    
                    # Truncate to reasonable length
                    if len(summary_text) > 2000:
                        summary_text = summary_text[:2000]
                    
                    print(f"   Creating summary from {len(chunks)} chunks ({len(summary_text)} chars)")
                    
                    # Generate embedding
                    print("   Generating embedding...")
                    doc_embedding = await embed_service.generate_embedding(summary_text)
                    
                    # Update document
                    doc.summary_text = summary_text
                    doc.embedding = doc_embedding
                    
                    await db.commit()
                    
                    print("   ✓ Embedding generated and saved")
                    processed += 1
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    failed += 1
                    await db.rollback()
                    continue
            
            # Summary
            print("\n" + "=" * 70)
            print("BACKFILL SUMMARY")
            print("=" * 70)
            print(f"✅ Successfully processed: {processed}")
            if failed > 0:
                print(f"❌ Failed: {failed}")
            print(f"📊 Total: {len(docs_without_embeddings)}")
            print("\n" + "=" * 70)
            
        except Exception as e:
            print(f"\n❌ Error during backfill: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(backfill_document_embeddings())
