import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.database.vector_db import vector_store
from sqlalchemy import text

def diagnose():
    with get_db() as db:
        # 1. Cek duplikat
        print("🔍 Checking for duplicates...")
        result = db.execute(text("""
            SELECT file_name, COUNT(*) as count 
            FROM documents 
            GROUP BY file_name 
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()
        
        if duplicates:
            print("❌ Found duplicates:")
            for dup in duplicates:
                print(f"   - {dup.file_name}: {dup.count} times")
        else:
            print("✅ No duplicates found")
        
        # 2. Cek chunks tanpa embeddings
        print("\n🔍 Checking chunks without embeddings...")
        result = db.execute(text("""
            SELECT COUNT(*) as count 
            FROM hadis_chunks 
            WHERE embedding IS NULL OR array_length(embedding, 1) = 0
        """))
        no_emb = result.fetchone()
        print(f"   Chunks without embeddings: {no_emb.count}")
        
        # 3. Cek index
        print("\n🔍 Checking HNSW index...")
        # ... tambahkan kode untuk cek index

if __name__ == "__main__":
    diagnose()