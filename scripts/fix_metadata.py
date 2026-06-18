import sys
import os
import asyncio

# Fix import path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.database.connection import get_db
from sqlalchemy import text

async def fix_metadata_and_deduplicate():
    print("🔄 FIXING METADATA & REMOVING TRUE DUPLICATES")
    print("=" * 70)
    
    async for db in get_db():
        try:
            # PHASE 1: Fix metadata for ID 2 (50 Hadits Pilihan)
            print("\n1️⃣  FIXING METADATA FOR 50 HADITS PILIHAN (ID 2):")
            
            update_query = text("""
                UPDATE hadis_documents 
                SET 
                    kitab_name = '50 Hadits Pilihan',
                    pengarang = 'DR. Muhammad Murtadha bin ''Aisy',
                    penerbit = 'Divisi Jaliyat',
                    tahun_terbit = 'Unknown',
                    filename = '50_Hadits_Pilihan_DR_Muhammad_Murtadha.pdf',
                    doc_metadata = jsonb_set(
                        COALESCE(doc_metadata, '{}'::jsonb),
                        '{description}',
                        '"Kumpulan 50 hadits pilihan dari berbagai kitab hadits"'
                    )
                WHERE id = 2
                RETURNING id, filename, kitab_name, pengarang
            """)
            
            result = await db.execute(update_query)
            fixed = result.fetchone()
            await db.commit()
            
            print(f"   ✅ Updated ID {fixed.id}:")
            print(f"      File: {fixed.filename}")
            print(f"      Kitab: {fixed.kitab_name}")
            print(f"      Pengarang: {fixed.pengarang}")
            
            # PHASE 2: Fix metadata for ID 16 (Shahih Bukhari)
            print("\n2️⃣  FIXING METADATA FOR SHAHIH BUKHARI (ID 16):")
            
            update_query = text("""
                UPDATE hadis_documents 
                SET 
                    kitab_name = 'Shahih Bukhari',
                    pengarang = 'Imam Bukhari',
                    penerbit = 'Unknown',
                    tahun_terbit = 'Unknown',
                    filename = 'Shahih_Bukhari_Lengkap.mysql',
                    doc_metadata = jsonb_set(
                        COALESCE(doc_metadata, '{}'::jsonb),
                        '{description}',
                        '"Shahih Bukhari lengkap - salah satu dari Kutubus Sittah"'
                    )
                WHERE id = 16
                RETURNING id, filename, kitab_name, pengarang
            """)
            
            result = await db.execute(update_query)
            fixed = result.fetchone()
            await db.commit()
            
            print(f"   ✅ Updated ID {fixed.id}:")
            print(f"      File: {fixed.filename}")
            print(f"      Kitab: {fixed.kitab_name}")
            print(f"      Pengarang: {fixed.pengarang}")
            
            # PHASE 3: Remove REAL duplicates (Musnad Ahmad yang double)
            print("\n3️⃣  CHECKING FOR REAL DUPLICATES:")
            
            # Cari file yang benar-benar sama (filename dan total_pages sama)
            result = await db.execute(text("""
                SELECT filename, total_pages, COUNT(*) as count,
                       ARRAY_AGG(id ORDER BY id) as ids,
                       ARRAY_AGG(kitab_name ORDER BY id) as kitab_names
                FROM hadis_documents 
                GROUP BY filename, total_pages
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """))
            
            true_duplicates = result.fetchall()
            
            if true_duplicates:
                print(f"   Found {len(true_duplicates)} true duplicate sets:")
                
                for dup in true_duplicates:
                    print(f"\n   📁 {dup.filename} ({dup.total_pages} pages):")
                    print(f"      {dup.count} duplicates - IDs: {dup.ids}")
                    print(f"      Kitab names: {dup.kitab_names}")
                    
                    # Hapus duplikat (simpan yang pertama)
                    if len(dup.ids) > 1:
                        ids_to_delete = dup.ids[1:]  # Semua kecuali yang pertama
                        print(f"      🗑️  Will delete IDs: {ids_to_delete}")
                        
                        for doc_id in ids_to_delete:
                            # Cek dulu chunks-nya
                            chunk_check = await db.execute(text("""
                                SELECT COUNT(*) as chunk_count 
                                FROM hadis_chunks 
                                WHERE document_id = :doc_id
                            """), {"doc_id": doc_id})
                            
                            chunk_count = chunk_check.fetchone().chunk_count
                            print(f"         • ID {doc_id} has {chunk_count} chunks")
                        
                        # Delete (akan cascade ke chunks)
                        delete_query = text("""
                            DELETE FROM hadis_documents 
                            WHERE id = ANY(:ids_to_delete)
                        """)
                        
                        await db.execute(delete_query, {"ids_to_delete": ids_to_delete})
                        await db.commit()
                        print(f"      ✅ Deleted {len(ids_to_delete)} duplicates")
            else:
                print("   ✅ No true duplicates found")
            
            # PHASE 4: Final verification
            print("\n4️⃣  FINAL DOCUMENT LIST:")
            
            result = await db.execute(text("""
                SELECT id, filename, kitab_name, pengarang, total_pages,
                       TO_CHAR(upload_date, 'YYYY-MM-DD') as upload_date
                FROM hadis_documents 
                ORDER BY kitab_name, id
            """))
            
            docs = result.fetchall()
            
            print(f"\n📚 Total documents: {len(docs)}")
            print("-" * 80)
            
            for doc in docs:
                print(f"📄 ID {doc.id}: {doc.filename}")
                print(f"   Kitab: {doc.kitab_name}")
                print(f"   Pengarang: {doc.pengarang or 'N/A'}")
                print(f"   Pages: {doc.total_pages} | Uploaded: {doc.upload_date}")
                print()
            
            break  # Keluar dari async generator setelah selesai
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            break

async def main():
    await fix_metadata_and_deduplicate()

if __name__ == "__main__":
    asyncio.run(main())