#!/usr/bin/env python3
"""
Script untuk regenerate embeddings - VERSION FIXED
Jalankan: python regenerate_embeddings_fixed.py --doc-ids 8,16,17
"""

import sys
import os
import asyncio
import argparse
from datetime import datetime
from typing import List, Optional

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.database.connection import get_db
from sqlalchemy import text
from app.services.embedding_service import get_embedding_service

async def regenerate_embeddings_fixed(
    doc_ids: Optional[List[int]] = None,
    batch_size: int = 32,
    skip_confirmation: bool = False
):
    """
    Regenerate embeddings dengan fix untuk struktur tabel yang benar
    """
    
    print("🔄 REGENERATE EMBEDDINGS - FIXED VERSION")
    print("=" * 70)
    
    # Initialize embedding service
    print("\n📦 Loading embedding service...")
    try:
        embedding_service = get_embedding_service()
        print("✅ Embedding service loaded")
    except Exception as e:
        print(f"❌ Failed to load embedding service: {e}")
        return
    
    # Test embedding service
    print("🧪 Testing embedding service...")
    try:
        test_embedding = await embedding_service.generate_embeddings(["Test hadits"])
        if test_embedding and len(test_embedding) > 0:
            dim = len(test_embedding[0])
            print(f"✅ Embedding dimension: {dim}")
        else:
            print("❌ Failed to generate test embedding")
            return
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return
    
    async for db in get_db():
        try:
            # ========== 1. BUILD QUERY BERDASARKAN FILTER ==========
            if doc_ids:
                # Filter by document IDs
                doc_ids_str = ','.join(map(str, doc_ids))
                count_query = text(f"""
                    SELECT COUNT(*) as total
                    FROM hadis_chunks
                    WHERE document_id IN ({doc_ids_str})
                """)
                
                select_query = text(f"""
                    SELECT 
                        hc.id,
                        hc.document_id,
                        hc.chunk_text,
                        hd.kitab_name
                    FROM hadis_chunks hc
                    JOIN hadis_documents hd ON hc.document_id = hd.id
                    WHERE hc.document_id IN ({doc_ids_str})
                    ORDER BY hc.document_id, hc.page_number, hc.chunk_index
                """)
                
                print(f"📋 Will process chunks from documents: {doc_ids}")
            else:
                # Process all chunks
                count_query = text("SELECT COUNT(*) as total FROM hadis_chunks")
                select_query = text("""
                    SELECT 
                        hc.id,
                        hc.document_id,
                        hc.chunk_text,
                        hd.kitab_name
                    FROM hadis_chunks hc
                    JOIN hadis_documents hd ON hc.document_id = hd.id
                    ORDER BY hc.document_id, hc.page_number, hc.chunk_index
                """)
                print("📋 Will process ALL chunks in database")
            
            # ========== 2. GET TOTAL COUNT ==========
            print("\n📊 Counting chunks...")
            result = await db.execute(count_query)
            total_chunks = result.fetchone().total
            
            if total_chunks == 0:
                print("⚠️  No chunks found")
                return
            
            print(f"   Total chunks to process: {total_chunks:,}")
            
            # ========== 3. USER CONFIRMATION ==========
            if not skip_confirmation:
                print("\n" + "=" * 70)
                print("⚠️  WARNING: This will regenerate embeddings for selected chunks")
                print("   Old embeddings will be overwritten!")
                print("=" * 70)
                
                confirm = input("\n❓ Continue? (yes/no): ").strip().lower()
                if confirm not in ['yes', 'y', 'ya']:
                    print("❌ Operation cancelled")
                    return
            
            # ========== 4. FETCH CHUNKS ==========
            print("\n📥 Fetching chunks...")
            result = await db.execute(select_query)
            chunks = result.fetchall()
            
            print(f"✅ Fetched {len(chunks):,} chunks")
            
            # ========== 5. PROCESS IN BATCHES ==========
            print("\n🔧 Processing embeddings...")
            start_time = datetime.now()
            processed = 0
            failed = 0
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(chunks) - 1) // batch_size + 1
                
                print(f"\r   Batch {batch_num}/{total_batches}: Processing {len(batch)} chunks...", end="")
                
                try:
                    # Extract texts
                    texts = [chunk.chunk_text for chunk in batch]
                    
                    # Generate embeddings
                    embeddings = await embedding_service.generate_embeddings(texts)
                    
                    if not embeddings or len(embeddings) != len(batch):
                        print(f"\n   ⚠️  Batch {batch_num}: Failed to generate embeddings")
                        failed += len(batch)
                        continue
                    
                    # Update database
                    for chunk, embedding in zip(batch, embeddings):
                        await db.execute(text("""
                            UPDATE hadis_chunks 
                            SET embedding = :embedding
                            WHERE id = :chunk_id
                        """), {"chunk_id": chunk.id, "embedding": embedding})
                    
                    await db.commit()
                    processed += len(batch)
                    
                except Exception as e:
                    print(f"\n   ❌ Batch {batch_num} error: {str(e)[:100]}...")
                    await db.rollback()
                    failed += len(batch)
            
            # ========== 6. CALCULATE STATS ==========
            duration = (datetime.now() - start_time).total_seconds()
            chunks_per_second = processed / duration if duration > 0 else 0
            
            print(f"\n\n✅ PROCESSING COMPLETE!")
            print("=" * 70)
            print(f"📊 Statistics:")
            print(f"   • Total chunks: {total_chunks:,}")
            print(f"   • Successfully processed: {processed:,}")
            print(f"   • Failed: {failed}")
            print(f"   • Duration: {duration:.1f} seconds")
            print(f"   • Speed: {chunks_per_second:.1f} chunks/second")
            
            # ========== 7. VERIFY ==========
            print("\n🔍 Verifying embeddings...")
            
            if doc_ids:
                doc_ids_str = ','.join(map(str, doc_ids))
                verify_query = text(f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embeddings,
                        ROUND(COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as coverage
                    FROM hadis_chunks
                    WHERE document_id IN ({doc_ids_str})
                """)
            else:
                verify_query = text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embeddings,
                        ROUND(COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as coverage
                    FROM hadis_chunks
                """)
            
            result = await db.execute(verify_query)
            verify_stats = result.fetchone()
            
            print(f"📈 Final coverage:")
            print(f"   • Total chunks: {verify_stats.total:,}")
            print(f"   • With embeddings: {verify_stats.with_embeddings:,}")
            print(f"   • Coverage: {verify_stats.coverage}%")
            
            if verify_stats.coverage == 100:
                print("\n🎉 SUCCESS: 100% coverage achieved!")
            elif verify_stats.coverage >= 95:
                print(f"\n✅ GOOD: {verify_stats.coverage}% coverage")
            else:
                print(f"\n⚠️  WARNING: Only {verify_stats.coverage}% coverage")
                print("   Consider running again")
            
            # ========== 8. NEXT STEPS ==========
            if processed > 0:
                print("\n🔧 Next steps:")
                print("   1. Test search functionality")
                print("   2. Monitor search accuracy")
                
                if doc_ids:
                    print(f"\n📋 Processed documents: {doc_ids}")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

async def regenerate_single_document(doc_id: int):
    """Regenerate embeddings for single document with progress"""
    
    print(f"🔄 Regenerating embeddings for document ID {doc_id}")
    print("=" * 60)
    
    async for db in get_db():
        try:
            # Get document info
            result = await db.execute(text("""
                SELECT kitab_name, filename 
                FROM hadis_documents 
                WHERE id = :doc_id
            """), {"doc_id": doc_id})
            
            doc_info = result.fetchone()
            if not doc_info:
                print(f"❌ Document {doc_id} not found")
                return
            
            print(f"📄 Document: {doc_info.kitab_name}")
            print(f"📁 File: {doc_info.filename}")
            
            # Count chunks
            result = await db.execute(text("""
                SELECT COUNT(*) as chunk_count
                FROM hadis_chunks
                WHERE document_id = :doc_id
            """), {"doc_id": doc_id})
            
            chunk_count = result.fetchone().chunk_count
            print(f"🧩 Chunks: {chunk_count:,}")
            
            if chunk_count == 0:
                print("⚠️  No chunks found for this document")
                return
            
            # Confirm
            confirm = input(f"\n❓ Regenerate embeddings for {chunk_count:,} chunks? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y', 'ya']:
                print("❌ Cancelled")
                return
            
            # Call main function
            await regenerate_embeddings_fixed(
                doc_ids=[doc_id],
                batch_size=32,
                skip_confirmation=True
            )
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Regenerate embeddings for hadis chunks")
    
    parser.add_argument(
        "--doc-id", 
        type=int,
        help="Regenerate embeddings for single document"
    )
    
    parser.add_argument(
        "--doc-ids",
        help="Regenerate embeddings for multiple documents (comma-separated)"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Regenerate embeddings for ALL documents"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for processing (default: 32)"
    )
    
    parser.add_argument(
        "--skip-confirmation",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if sum([args.doc_id is not None, args.doc_ids is not None, args.all]) > 1:
        print("❌ Error: Please specify only one of --doc-id, --doc-ids, or --all")
        return
    
    if args.doc_id:
        await regenerate_single_document(args.doc_id)
    
    elif args.doc_ids:
        doc_ids = [int(id_str.strip()) for id_str in args.doc_ids.split(",")]
        await regenerate_embeddings_fixed(
            doc_ids=doc_ids,
            batch_size=args.batch_size,
            skip_confirmation=args.skip_confirmation
        )
    
    elif args.all:
        confirm = input("\n⚠️  WARNING: This will regenerate ALL embeddings in database!\n❓ Continue? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y', 'ya']:
            await regenerate_embeddings_fixed(
                doc_ids=None,  # Process all
                batch_size=args.batch_size,
                skip_confirmation=True
            )
        else:
            print("❌ Cancelled")
    
    else:
        print("🔧 EMBEDDINGS REGENERATION TOOL")
        print("=" * 60)
        print("\nUsage options:")
        print("  1. Single document:")
        print("     python regenerate_embeddings_fixed.py --doc-id 8")
        print()
        print("  2. Multiple documents:")
        print("     python regenerate_embeddings_fixed.py --doc-ids 8,16,17")
        print()
        print("  3. All documents (use with caution!):")
        print("     python regenerate_embeddings_fixed.py --all")
        print()
        print("  4. With custom batch size:")
        print("     python regenerate_embeddings_fixed.py --doc-ids 8,16 --batch-size 64")
        print()
        print("📝 Example based on your needs:")
        print("   python regenerate_embeddings_fixed.py --doc-ids 8,16,17")

if __name__ == "__main__":
    asyncio.run(main())