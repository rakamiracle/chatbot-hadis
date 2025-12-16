import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from app.database.connection import AsyncSessionLocal
from app.models.document import HadisDocument, DocumentStatus
from app.models.chunk import HadisChunk
from app.services.embedding_service import EmbeddingService
from datetime import datetime

# ===================================
# 🔧 CONFIG - SESUAIKAN DENGAN DATABASE MYSQL KATING
# ===================================
MYSQL_CONFIG = {
    "host": "localhost",  # Atau IP server MySQL 
    "user": "root",       # Username MySQL
    "password": "root12345678",       # Password MySQL 
    "database": "hadis_kating",  # Nama database di MySQL
    "charset": "utf8mb4"
}

TABLES_TO_IMPORT = [
    # {"name": "musnad_ahmad", "kitab_name": "Musnad Ahmad"},
    # {"name": "musnad_darimi", "kitab_name": "Musnad Darimi"},
    {"name": "musnad_syafii", "kitab_name": "Musnad Syafi'i"}, 
    # {"name": "muwatho_malik", "kitab_name": "Muwatho Malik"},
    # {"name": "riyadhus_shalihin", "kitab_name": "Riyadhus Shalihin"},
    {"name": "shahih_bukhari", "kitab_name": "Shahih Bukhari"}, 
    {"name": "shahih_muslim", "kitab_name": "Shahih Muslim"}, 
    {"name": "sunan_abu_daud", "kitab_name": "Sunan Abu Daud"}, 
    {"name": "sunan_ibnu_majah", "kitab_name": "Sunan Ibnu Majah"}, 
    {"name": "sunan_nasai", "kitab_name": "Sunan Nasai"},
    {"name": "sunan_tirmidzi", "kitab_name": "Sunan Tirmidzi"},
]
# ===================================

async def import_from_mysql():
    """Import hadis langsung dari MySQL"""
    
    print("=" * 70)
    print("📥 IMPORT HADIS DARI MYSQL DATABASE KATING")
    print("=" * 70)
    
    # Connect ke MySQL
    try:
        print("\n🔌 Connecting to MySQL...")
        mysql_conn = pymysql.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor(pymysql.cursors.DictCursor)
        print("   ✓ Connected to MySQL!")
    except Exception as e:
        print(f"   ❌ Failed to connect to MySQL: {e}")
        print("\n💡 Tips:")
        print("   - Pastikan MySQL server running")
        print("   - Cek MYSQL_CONFIG (host, user, password, database)")
        print("   - Install: pip install pymysql")
        return
    
    embed_service = EmbeddingService()
    total_imported = 0
    
    async with AsyncSessionLocal() as db:
        try:
            for table_config in TABLES_TO_IMPORT:
                table_name = table_config["name"]
                kitab_name = table_config["kitab_name"]
                
                print(f"\n{'='*70}")
                print(f"📖 Processing: {kitab_name}")
                print(f"{'='*70}")
                
                # 1. Count hadis
                print("\n1️⃣ Counting hadis...")
                mysql_cursor.execute(f"SELECT COUNT(*) as total FROM {table_name}")
                total_hadis = mysql_cursor.fetchone()['total']
                
                print(f"   ✓ Found {total_hadis:,} hadis")
                
                if total_hadis == 0:
                    print(f"   ⚠️  Table {table_name} empty, skipping...")
                    continue
                
                # 2. Create document
                print("\n2️⃣ Creating document entry...")
                doc = HadisDocument(
                    filename=f"{kitab_name}.mysql",
                    kitab_name=kitab_name,
                    total_pages=total_hadis,
                    status=DocumentStatus.PROCESSING,
                    doc_metadata={
                        "source": "mysql_kating",
                        "table": table_name,
                        "import_date": datetime.utcnow().isoformat()
                    }
                )
                db.add(doc)
                await db.flush()
                await db.refresh(doc)
                
                print(f"   ✓ Document ID: {doc.id}")
                
                # 3. Process dalam batch
                print("\n3️⃣ Reading and generating embeddings...")
                batch_size = 50
                chunks_created = 0
                offset = 0
                
                while offset < total_hadis:
                    # Read batch dari MySQL
                    query = f"""
                        SELECT id, terjemah, Bab, arab 
                        FROM {table_name} 
                        ORDER BY id 
                        LIMIT {batch_size} OFFSET {offset}
                    """
                    mysql_cursor.execute(query)
                    batch = mysql_cursor.fetchall()
                    
                    if not batch:
                        break
                    
                    # Generate embeddings
                    texts = [row['terjemah'] for row in batch]
                    embeddings = await embed_service.generate_embeddings_batch(texts)
                    
                    # Create chunks
                    for row, embedding in zip(batch, embeddings):
                        chunk = HadisChunk(
                            document_id=doc.id,
                            chunk_text=row['terjemah'],
                            chunk_index=row['id'],
                            page_number=row['id'],
                            embedding=embedding,
                            chunk_metadata={
                                "kitab": kitab_name,
                                "bab": row['Bab'],
                                "hadis_id": str(row['id']),
                                "arab": row['arab'][:200] if row.get('arab') else None,
                                "source": "mysql_kating"
                            }
                        )
                        db.add(chunk)
                        chunks_created += 1
                    
                    await db.flush()
                    
                    offset += batch_size
                    progress = min(offset, total_hadis)
                    print(f"   • Progress: {progress:,}/{total_hadis:,} ({progress/total_hadis*100:.1f}%)")
                
                # Update status
                doc.status = DocumentStatus.COMPLETED
                await db.commit()
                
                print(f"\n   ✅ {kitab_name}: {chunks_created:,} hadis imported")
                total_imported += chunks_created
            
            # Summary
            print("\n" + "=" * 70)
            print("✅ IMPORT COMPLETE!")
            print("=" * 70)
            print(f"📊 Total hadis imported: {total_imported:,}")
            print(f"📚 Total kitab: {len(TABLES_TO_IMPORT)}")
            print("\n🎉 Database ready to use!")
            print("\nTest: streamlit run streamlit_app.py")
            print("=" * 70)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
        finally:
            mysql_cursor.close()
            mysql_conn.close()
            print("\n🔌 MySQL connection closed")

if __name__ == "__main__":
    print("\n⚠️  REQUIREMENTS:")
    print("1. MySQL server running")
    print("2. pip install pymysql")
    print("3. Edit MYSQL_CONFIG (host, user, password, database)")
    print("")
    
    input("Press ENTER to continue...")
    
    asyncio.run(import_from_mysql())