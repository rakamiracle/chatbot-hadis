#!/usr/bin/env python3
"""
REGERATE EMBEDDINGS - Correct version matching your EmbeddingService API
Jalankan: python regenerate_correct.py --doc-ids 8,16,17
"""

import sys
import os
import asyncio
import argparse

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from sqlalchemy import text

async def regenerate_correct(doc_ids=None):
    """Regenerate embeddings dengan API yang benar"""
    
    print("🔄 EMBEDDINGS REGENERATION - CORRECT VERSION")
    print("=" * 60)
    
    # Coba semua kemungkinan method dari EmbeddingService
    try:
        from app.services.embedding_service import EmbeddingService
        
        # Instantiate service
        embedding_service = EmbeddingService()
        print("✅ EmbeddingService instantiated")
        
        # TEST: Coba method yang ada
        test_text = "test hadis"
        
        # Coba berbagai kemungkinan method
        possible_methods = [
            'generate_embeddings',    # plural
            'generate_embedding',     # singular  
            'embed',                  # simple name
            'get_embedding',          # get prefix
            'create_embedding',       # create prefix
            'encode'                  # encode
        ]
        
        working_method = None
        for method_name in possible_methods:
            if hasattr(embedding_service, method_name):
                try:
                    method = getattr(embedding_service, method_name)
                    # Coba panggil
                    if asyncio.iscoroutinefunction(method):
                        result = await method([test_text])
                    else:
                        result = method([test_text])
                    
                    if result and len(result) > 0:
                        working_method = method_name
                        print(f"✅ Found working method: {method_name}()")
                        print(f"   Embedding dimension: {len(result[0])}")
                        break
                except:
                    continue
        
        if not working_method:
            print("❌ Cannot find working embedding method!")
            print("   Available methods in EmbeddingService:")
            for attr in dir(embedding_service):
                if not attr.startswith('_'):
                    print(f"   - {attr}")
            return
            
    except ImportError as e:
        print(f"❌ Cannot import EmbeddingService: {e}")
        return
    
    from app.database.connection import get_db
    
    async for db in get_db():
        try:
            # Build query based on filter
            if doc_ids:
                doc_ids_str = ','.join(map(str, doc_ids))
                print(f"📋 Processing documents: {doc_ids}")
                
                # Get document info first
                result = await db.execute(text(f"""
                    SELECT id, kitab_name 
                    FROM hadis_documents 
                    WHERE id IN ({doc_ids_str})
                    ORDER BY id
                """))
                
                docs = result.fetchall()
                print(f"📚 Documents to process:")
                for doc in docs:
                    print(f"   • ID {doc.id}: {doc.kitab_name}")
                
                count_query = text(f"""
                    SELECT COUNT(*) as total
                    FROM hadis_chunks
                    WHERE document_id IN ({doc_ids_str})
                """)
                
                select_query = text(f"""
                    SELECT id, chunk_text, document_id
                    FROM hadis_chunks
                    WHERE document_id IN ({doc_ids_str})
                    ORDER BY document_id, page_number, chunk_index
                """)
            else:
                print("📋 Processing ALL documents")
                count_query = text("SELECT COUNT(*) as total FROM hadis_chunks")
                select_query = text("""
                    SELECT id, chunk_text, document_id
                    FROM hadis_chunks
                    ORDER BY document_id, page_number, chunk_index
                """)
            
            # Get total count
            result = await db.execute(count_query)
            total = result.fetchone().total
            
            if total == 0:
                print("⚠️  No chunks found")
                return
            
            print(f"\n📊 Total chunks to process: {total:,}")
            
            # Confirmation
            confirm = input(f"\n❓ Regenerate embeddings for {total:,} chunks? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y', 'ya']:
                print("❌ Cancelled")
                return
            
            # Fetch all chunks
            print("\n📥 Fetching chunks...")
            result = await db.execute(select_query)
            chunks = result.fetchall()
            
            print(f"✅ Fetched {len(chunks):,} chunks")
            
            # Process in batches
            batch_size = 16  # Smaller batch for safety
            processed = 0
            failed = 0
            
            print(f"\n🔧 Processing using {working_method}()...")
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(chunks) - 1) // batch_size + 1
                
                print(f"\r   Batch {batch_num}/{total_batches}: Processing {len(batch)} chunks", end="", flush=True)
                
                try:
                    # Extract texts
                    texts = [chunk.chunk_text for chunk in batch]
                    
                    # Get the method
                    method = getattr(embedding_service, working_method)
                    
                    # Call the method
                    if asyncio.iscoroutinefunction(method):
                        embeddings = await method(texts)
                    else:
                        embeddings = method(texts)
                    
                    # Check result
                    if not embeddings:
                        print(f"\n   ⚠️  Batch {batch_num}: No embeddings returned")
                        failed += len(batch)
                        continue
                    
                    if len(embeddings) != len(batch):
                        print(f"\n   ⚠️  Batch {batch_num}: Mismatch - got {len(embeddings)} embeddings for {len(batch)} texts")
                        failed += len(batch)
                        continue
                    
                    # Update database
                    for chunk, emb in zip(batch, embeddings):
                        await db.execute(text("""
                            UPDATE hadis_chunks 
                            SET embedding = :embedding
                            WHERE id = :chunk_id
                        """), {"chunk_id": chunk.id, "embedding": emb})
                    
                    await db.commit()
                    processed += len(batch)
                    
                except Exception as e:
                    print(f"\n   ❌ Batch {batch_num} error: {str(e)[:100]}")
                    failed += len(batch)
                    await db.rollback()
            
            print(f"\n\n✅ COMPLETE!")
            print("=" * 60)
            print(f"📊 Results:")
            print(f"   • Total chunks: {total:,}")
            print(f"   • Successfully processed: {processed:,}")
            print(f"   • Failed: {failed}")
            
            if processed > 0:
                success_rate = (processed / total) * 100
                print(f"   • Success rate: {success_rate:.1f}%")
                
                # Verify
                if doc_ids:
                    verify_query = text(f"""
                        SELECT 
                            COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embeddings
                        FROM hadis_chunks
                        WHERE document_id IN ({doc_ids_str})
                    """)
                else:
                    verify_query = text("""
                        SELECT COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embeddings
                        FROM hadis_chunks
                    """)
                
                result = await db.execute(verify_query)
                with_emb = result.fetchone().with_embeddings
                
                print(f"\n📈 Final coverage: {with_emb:,}/{total:,} ({with_emb/total*100:.1f}%)")
                print("\n🎉 Embeddings regenerated successfully!")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

async def main():
    parser = argparse.ArgumentParser(description="Correct embeddings regeneration")
    parser.add_argument("--doc-ids", help="Document IDs (comma-separated)")
    parser.add_argument("--all", action="store_true", help="Process all documents")
    
    args = parser.parse_args()
    
    if args.all:
        confirm = input("\n⚠️  Process ALL documents? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y', 'ya']:
            await regenerate_correct(None)
        else:
            print("❌ Cancelled")
    elif args.doc_ids:
        doc_ids = [int(id_str.strip()) for id_str in args.doc_ids.split(",")]
        await regenerate_correct(doc_ids)
    else:
        print("🔧 CORRECT EMBEDDINGS REGENERATION")
        print("=" * 60)
        print("\nUsage:")
        print("  python regenerate_correct.py --doc-ids 8,16,17")
        print("  python regenerate_correct.py --all")
        print("\nExample untuk dokumen hasil optimize:")
        print("  python regenerate_correct.py --doc-ids 8,16,17")

if __name__ == "__main__":
    asyncio.run(main())