#!/usr/bin/env python3
"""
Quick script untuk cek vector database
"""
import os
import sys

# Set path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    try:
        import asyncio
        from sqlalchemy import select, func, text
        from app.database.connection import get_db
        from app.models.chunk import HadisChunk
        from app.models.document import HadisDocument
        from app.models.chat_history import ChatHistory
        
        async def check():
            async for db in get_db():
                try:
                    print("\n" + "="*60)
                    print("🔍 VECTOR DATABASE STATUS")
                    print("="*60 + "\n")
                    
                    # 1. Chunks
                    result = await db.execute(select(func.count(HadisChunk.id)))
                    total_chunks = result.scalar() or 0
                    
                    result = await db.execute(
                        select(func.count(HadisChunk.id))
                        .where(HadisChunk.embedding.isnot(None))
                    )
                    chunks_with_emb = result.scalar() or 0
                    
                    print(f"📦 HADIS CHUNKS:")
                    print(f"   Total: {total_chunks}")
                    print(f"   With embeddings: {chunks_with_emb}")
                    if total_chunks > 0:
                        print(f"   Coverage: {chunks_with_emb/total_chunks*100:.1f}%")
                    
                    # Sample chunk
                    if chunks_with_emb > 0:
                        result = await db.execute(
                            select(HadisChunk)
                            .where(HadisChunk.embedding.isnot(None))
                            .limit(1)
                        )
                        chunk = result.scalar_one_or_none()
                        if chunk:
                            print(f"\n   📝 Sample chunk:")
                            print(f"      Text: {chunk.chunk_text[:80]}...")
                            print(f"      Vector: {str(chunk.embedding)[:80]}...")
                    
                    # 2. Documents
                    print(f"\n📚 DOCUMENTS:")
                    result = await db.execute(select(func.count(HadisDocument.id)))
                    total_docs = result.scalar() or 0
                    
                    result = await db.execute(
                        select(func.count(HadisDocument.id))
                        .where(HadisDocument.embedding.isnot(None))
                    )
                    docs_with_emb = result.scalar() or 0
                    
                    print(f"   Total: {total_docs}")
                    print(f"   With embeddings: {docs_with_emb}")
                    
                    # 3. Chat History
                    print(f"\n💬 CHAT HISTORY:")
                    result = await db.execute(select(func.count(ChatHistory.id)))
                    total_chats = result.scalar() or 0
                    
                    result = await db.execute(
                        select(func.count(ChatHistory.id))
                        .where(ChatHistory.query_embedding.isnot(None))
                    )
                    chats_with_emb = result.scalar() or 0
                    
                    print(f"   Total: {total_chats}")
                    print(f"   With embeddings: {chats_with_emb}")
                    
                    # 4. HNSW Index
                    print(f"\n🔧 HNSW INDEX:")
                    result = await db.execute(text("""
                        SELECT COUNT(*) FROM pg_indexes 
                        WHERE tablename = 'hadis_chunks' 
                        AND indexdef LIKE '%hnsw%'
                    """))
                    has_index = result.scalar() > 0
                    print(f"   Status: {'✅ EXISTS' if has_index else '❌ NOT FOUND'}")
                    
                    print("\n" + "="*60)
                    print("✅ Done!")
                    print("="*60 + "\n")
                    
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    break
        
        asyncio.run(check())
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("\nPastikan:")
        print("1. Virtual environment sudah aktif: source venv/bin/activate")
        print("2. Dependencies sudah terinstall: pip install -r requirements.txt")
        print("3. Database URL sudah di-set di .env\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
