"""
Script untuk mengecek isi vector database
Jalankan: python scripts/check_vector_db.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from app.database.connection import get_db
from app.models.document import HadisDocument
from app.models.chunk import HadisChunk

async def check_vector_database():
    """Check what's in the vector database"""
    
    async for db in get_db():
        try:
            print("=" * 70)
            print("DOKUMEN YANG SUDAH DI-UPLOAD KE VECTOR DATABASE")
            print("=" * 70)
            
            # Get all documents
            result = await db.execute(
                select(HadisDocument).order_by(HadisDocument.id)
            )
            docs = result.scalars().all()
            
            print(f"\n📚 Total Dokumen: {len(docs)}\n")
            
            if len(docs) == 0:
                print("⚠️  Belum ada dokumen yang di-upload!")
                print("\nCara upload dokumen:")
                print("1. Jalankan backend: python run.py")
                print("2. Buka Streamlit: streamlit run streamlit_app.py")
                print("3. Upload PDF hadis melalui sidebar\n")
            else:
                for i, doc in enumerate(docs, 1):
                    print(f"{i}. 📖 {doc.kitab_name or 'Unknown Kitab'}")
                    print(f"   File: {doc.filename}")
                    print(f"   ID: {doc.id}")
                    print(f"   Status: {doc.status}")
                    print(f"   Total Pages: {doc.total_pages}")
                    print(f"   Upload Date: {doc.upload_date}")
                    
                    # Get chunk count for this document
                    chunk_result = await db.execute(
                        select(func.count(HadisChunk.id))
                        .where(HadisChunk.document_id == doc.id)
                    )
                    chunk_count = chunk_result.scalar()
                    print(f"   Chunks: {chunk_count}")
                    print()
            
            # Get total chunks
            total_result = await db.execute(select(func.count(HadisChunk.id)))
            total_chunks = total_result.scalar()
            
            print("=" * 70)
            print("CHUNKS/EMBEDDINGS DI VECTOR DATABASE")
            print("=" * 70)
            print(f"\n🔢 Total Chunks dengan Embeddings: {total_chunks}")
            
            if total_chunks > 0:
                print("\n📊 Detail per Kitab:")
                for doc in docs:
                    result = await db.execute(
                        select(func.count(HadisChunk.id))
                        .where(HadisChunk.document_id == doc.id)
                    )
                    chunk_count = result.scalar()
                    kitab_name = doc.kitab_name or doc.filename
                    print(f"   • {kitab_name}: {chunk_count} chunks")
            
            print("\n" + "=" * 70)
            print("✅ Selesai!")
            print("=" * 70 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(check_vector_database())
