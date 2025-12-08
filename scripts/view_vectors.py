"""
Script untuk melihat data yang sudah di-vector-kan di database
Jalankan: python scripts/view_vectors.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func, text
from app.database.connection import get_db
from app.models.document import HadisDocument
from app.models.chunk import HadisChunk
from app.models.chat_history import ChatHistory

async def view_vectorized_data():
    """Lihat data yang sudah di-vector-kan"""
    
    async for db in get_db():
        try:
            print("=" * 80)
            print("📊 DATA YANG SUDAH DI-VECTOR-KAN")
            print("=" * 80)
            
            # ========== 1. HADIS CHUNKS ==========
            print("\n" + "=" * 80)
            print("1️⃣  HADIS CHUNKS (Chunks dengan Embeddings)")
            print("=" * 80)
            
            # Total chunks
            result = await db.execute(select(func.count(HadisChunk.id)))
            total_chunks = result.scalar()
            
            # Chunks dengan embeddings
            result = await db.execute(
                select(func.count(HadisChunk.id))
                .where(HadisChunk.embedding.isnot(None))
            )
            chunks_with_emb = result.scalar()
            
            print(f"\n📈 Total Chunks: {total_chunks}")
            print(f"✅ Chunks dengan Embeddings: {chunks_with_emb}")
            print(f"📊 Coverage: {(chunks_with_emb/total_chunks*100) if total_chunks > 0 else 0:.1f}%")
            
            # Sample chunks dengan embeddings
            if chunks_with_emb > 0:
                print("\n📝 Sample Chunks dengan Embeddings:")
                result = await db.execute(
                    select(HadisChunk)
                    .where(HadisChunk.embedding.isnot(None))
                    .limit(3)
                )
                chunks = result.scalars().all()
                
                for i, chunk in enumerate(chunks, 1):
                    print(f"\n   [{i}] Chunk ID: {chunk.id}")
                    print(f"       Document ID: {chunk.document_id}")
                    print(f"       Page: {chunk.page_number}")
                    print(f"       Text Preview: {chunk.chunk_text[:100]}...")
                    
                    # Tampilkan beberapa nilai embedding
                    if chunk.embedding:
                        emb_preview = str(chunk.embedding)[:100]
                        print(f"       Embedding: {emb_preview}... (384 dimensions)")
            
            # ========== 2. HADIS DOCUMENTS ==========
            print("\n" + "=" * 80)
            print("2️⃣  HADIS DOCUMENTS (Dokumen dengan Embeddings)")
            print("=" * 80)
            
            # Total documents
            result = await db.execute(select(func.count(HadisDocument.id)))
            total_docs = result.scalar()
            
            # Documents dengan embeddings
            result = await db.execute(
                select(func.count(HadisDocument.id))
                .where(HadisDocument.embedding.isnot(None))
            )
            docs_with_emb = result.scalar()
            
            print(f"\n📈 Total Documents: {total_docs}")
            print(f"✅ Documents dengan Embeddings: {docs_with_emb}")
            print(f"📊 Coverage: {(docs_with_emb/total_docs*100) if total_docs > 0 else 0:.1f}%")
            
            # List semua documents
            if total_docs > 0:
                print("\n📚 Daftar Documents:")
                result = await db.execute(
                    select(HadisDocument).order_by(HadisDocument.id)
                )
                docs = result.scalars().all()
                
                for i, doc in enumerate(docs, 1):
                    has_emb = "✅" if doc.embedding else "❌"
                    print(f"\n   [{i}] {has_emb} {doc.kitab_name or doc.filename}")
                    print(f"       ID: {doc.id}")
                    print(f"       Status: {doc.status}")
                    print(f"       Pages: {doc.total_pages}")
                    if doc.summary_text:
                        print(f"       Summary: {doc.summary_text[:80]}...")
                    if doc.embedding:
                        emb_preview = str(doc.embedding)[:100]
                        print(f"       Embedding: {emb_preview}...")
            
            # ========== 3. CHAT HISTORY ==========
            print("\n" + "=" * 80)
            print("3️⃣  CHAT HISTORY (Chat dengan Embeddings)")
            print("=" * 80)
            
            # Total chats
            result = await db.execute(select(func.count(ChatHistory.id)))
            total_chats = result.scalar()
            
            # Chats dengan embeddings
            result = await db.execute(
                select(func.count(ChatHistory.id))
                .where(ChatHistory.query_embedding.isnot(None))
            )
            chats_with_emb = result.scalar()
            
            print(f"\n📈 Total Chat History: {total_chats}")
            print(f"✅ Chats dengan Query Embeddings: {chats_with_emb}")
            print(f"📊 Coverage: {(chats_with_emb/total_chats*100) if total_chats > 0 else 0:.1f}%")
            
            # Sample chats
            if chats_with_emb > 0:
                print("\n💬 Sample Chat dengan Embeddings:")
                result = await db.execute(
                    select(ChatHistory)
                    .where(ChatHistory.query_embedding.isnot(None))
                    .order_by(ChatHistory.timestamp.desc())
                    .limit(3)
                )
                chats = result.scalars().all()
                
                for i, chat in enumerate(chats, 1):
                    print(f"\n   [{i}] Chat ID: {chat.id}")
                    print(f"       Time: {chat.timestamp}")
                    print(f"       Query: {chat.user_query[:80]}...")
                    print(f"       Response: {chat.bot_response[:80]}...")
                    
                    # Check embeddings
                    emb_status = []
                    if chat.query_embedding:
                        emb_status.append("query ✅")
                    if chat.response_embedding:
                        emb_status.append("response ✅")
                    if chat.combined_embedding:
                        emb_status.append("combined ✅")
                    print(f"       Embeddings: {', '.join(emb_status)}")
            
            # ========== 4. VECTOR INDEXES ==========
            print("\n" + "=" * 80)
            print("4️⃣  VECTOR INDEXES (HNSW)")
            print("=" * 80)
            
            result = await db.execute(text("""
                SELECT 
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE indexdef LIKE '%hnsw%'
                ORDER BY tablename, indexname
            """))
            indexes = result.fetchall()
            
            if indexes:
                print(f"\n✅ Found {len(indexes)} HNSW index(es):")
                for idx in indexes:
                    print(f"\n   📌 Table: {idx[0]}")
                    print(f"      Index: {idx[1]}")
                    print(f"      Definition: {idx[2][:100]}...")
            else:
                print("\n⚠️  No HNSW indexes found!")
                print("   Run: python scripts/add_vector_index.py")
            
            # ========== 5. STORAGE SIZE ==========
            print("\n" + "=" * 80)
            print("5️⃣  STORAGE SIZE")
            print("=" * 80)
            
            result = await db.execute(text("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size
                FROM pg_tables
                WHERE tablename IN ('hadis_chunks', 'hadis_documents', 'chat_history')
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """))
            sizes = result.fetchall()
            
            print("\n💾 Table Sizes:")
            for size in sizes:
                print(f"   • {size[0]}: {size[1]} (table: {size[2]})")
            
            # ========== SUMMARY ==========
            print("\n" + "=" * 80)
            print("📊 SUMMARY")
            print("=" * 80)
            print(f"""
✅ Hadis Chunks:    {chunks_with_emb}/{total_chunks} vectorized
✅ Documents:       {docs_with_emb}/{total_docs} vectorized
✅ Chat History:    {chats_with_emb}/{total_chats} vectorized
✅ HNSW Indexes:    {len(indexes)} found
            """)
            
            print("=" * 80)
            print("✅ Selesai!")
            print("=" * 80 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(view_vectorized_data())
