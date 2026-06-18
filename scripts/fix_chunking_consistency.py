import sys
import os
import asyncio
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.database.connection import get_db
from sqlalchemy import text
from typing import List, Tuple

class ChunkingFixer:
    def __init__(self):
        self.target_chunk_size = 1000  # characters
        self.min_chunk_size = 500
        self.max_chunk_size = 1500
        self.overlap_size = 100  # characters overlap between chunks
    
    async def analyze_document(self, db, doc_id: int) -> dict:
        """Analyze a document's chunking pattern"""
        
        result = await db.execute(text("""
            SELECT 
                hd.id,
                hd.filename,
                hd.kitab_name,
                hd.total_pages,
                COUNT(hc.id) as total_chunks,
                AVG(LENGTH(hc.chunk_text)) as avg_chunk_size,
                MIN(LENGTH(hc.chunk_text)) as min_chunk_size,
                MAX(LENGTH(hc.chunk_text)) as max_chunk_size,
                STDDEV(LENGTH(hc.chunk_text)) as size_stddev
            FROM hadis_documents hd
            LEFT JOIN hadis_chunks hc ON hd.id = hc.document_id
            WHERE hd.id = :doc_id
            GROUP BY hd.id, hd.filename, hd.kitab_name, hd.total_pages
        """), {"doc_id": doc_id})
        
        doc_info = result.fetchone()
        
        if not doc_info:
            return None
        
        # Get chunk samples
        result = await db.execute(text("""
            SELECT chunk_text, page_number, LENGTH(chunk_text) as size
            FROM hadis_chunks
            WHERE document_id = :doc_id
            ORDER BY page_number, id
            LIMIT 10
        """), {"doc_id": doc_id})
        
        samples = result.fetchall()
        
        # Calculate issues
        issues = []
        
        if doc_info.size_stddev and doc_info.size_stddev > 500:
            issues.append(f"High size variance (stddev: {doc_info.size_stddev:.0f})")
        
        if doc_info.avg_chunk_size and doc_info.avg_chunk_size < self.min_chunk_size:
            issues.append(f"Chunks too small (avg: {doc_info.avg_chunk_size:.0f} chars)")
        
        if doc_info.avg_chunk_size and doc_info.avg_chunk_size > self.max_chunk_size:
            issues.append(f"Chunks too large (avg: {doc_info.avg_chunk_size:.0f} chars)")
        
        if doc_info.total_pages and doc_info.total_chunks:
            ratio = doc_info.total_chunks / doc_info.total_pages
            if ratio < 0.5:
                issues.append(f"Under-chunked ({ratio:.2f} chunks/page)")
            elif ratio > 2.0:
                issues.append(f"Over-chunked ({ratio:.2f} chunks/page)")
        
        return {
            "id": doc_info.id,
            "filename": doc_info.filename,
            "kitab_name": doc_info.kitab_name,
            "total_pages": doc_info.total_pages,
            "total_chunks": doc_info.total_chunks,
            "avg_chunk_size": doc_info.avg_chunk_size,
            "min_chunk_size": doc_info.min_chunk_size,
            "max_chunk_size": doc_info.max_chunk_size,
            "size_stddev": doc_info.size_stddev,
            "issues": issues,
            "samples": samples
        }
    
    def split_text_into_chunks(self, text: str, page_number: int) -> List[Tuple[str, int]]:
        """Split text into chunks with overlap"""
        chunks = []
        
        # Jika text terlalu kecil, jangan split
        if len(text) <= self.max_chunk_size:
            return [(text, page_number)]
        
        # Split by sentences jika ada
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.max_chunk_size and current_chunk:
                # Finalize current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append((chunk_text, page_number))
                
                # Start new chunk dengan overlap
                overlap_start = max(0, len(current_chunk) - 3)  # last 3 sentences
                current_chunk = current_chunk[overlap_start:]
                current_chunk.append(sentence)
                current_size = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append((chunk_text, page_number))
        
        return chunks
    
    async def rechunk_document(self, db, doc_id: int):
        """Re-chunk a document with consistent sizing"""
        
        print(f"\n🔧 Re-chunking document ID {doc_id}...")
        
        # Get all chunks for this document
        result = await db.execute(text("""
            SELECT id, page_number, chunk_text
            FROM hadis_chunks
            WHERE document_id = :doc_id
            ORDER BY page_number, id
        """), {"doc_id": doc_id})
        
        chunks = result.fetchall()
        
        if not chunks:
            print(f"   ⚠️  No chunks found for document {doc_id}")
            return 0
        
        # Group by page
        pages = {}
        for chunk in chunks:
            page_num = chunk.page_number
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(chunk.chunk_text)
        
        # Combine text per page
        page_texts = {}
        for page_num, text_list in pages.items():
            page_texts[page_num] = ' '.join(text_list)
        
        # Delete old chunks
        print(f"   🗑️  Deleting {len(chunks)} old chunks...")
        await db.execute(text("DELETE FROM hadis_chunks WHERE document_id = :doc_id"), 
                        {"doc_id": doc_id})
        
        # Create new chunks
        new_chunks = []
        chunk_counter = 0
        
        for page_num, text in sorted(page_texts.items()):
            chunks_for_page = self.split_text_into_chunks(text, page_num)
            
            for chunk_text, chunk_page_num in chunks_for_page:
                if self.min_chunk_size <= len(chunk_text) <= self.max_chunk_size:
                    new_chunks.append({
                        "document_id": doc_id,
                        "page_number": chunk_page_num,
                        "chunk_text": chunk_text,
                        "chunk_order": chunk_counter
                    })
                    chunk_counter += 1
        
        # Insert new chunks
        print(f"   📝 Inserting {len(new_chunks)} new chunks...")
        
        for chunk in new_chunks:
            await db.execute(text("""
                INSERT INTO hadis_chunks 
                (document_id, page_number, chunk_text, chunk_order)
                VALUES (:document_id, :page_number, :chunk_text, :chunk_order)
            """), chunk)
        
        await db.commit()
        
        # Update embeddings status (will need re-embedding)
        await db.execute(text("""
            UPDATE hadis_chunks 
            SET embedding = NULL
            WHERE document_id = :doc_id
        """), {"doc_id": doc_id})
        
        await db.commit()
        
        print(f"   ✅ Created {len(new_chunks)} chunks (avg size: {sum(len(c['chunk_text']) for c in new_chunks)/len(new_chunks):.0f} chars)")
        
        return len(new_chunks)

async def main():
    print("🔄 FIXING CHUNKING CONSISTENCY")
    print("=" * 60)
    
    fixer = ChunkingFixer()
    
    async for db in get_db():
        try:
            # 1. Identify inconsistent documents
            print("\n🔍 Identifying inconsistent documents...")
            
            result = await db.execute(text("""
                SELECT 
                    hd.id,
                    hd.filename,
                    hd.kitab_name,
                    hd.total_pages,
                    COUNT(hc.id) as total_chunks,
                    ROUND(COUNT(hc.id)::decimal / NULLIF(hd.total_pages, 0), 2) as chunks_per_page,
                    ROUND(AVG(LENGTH(hc.chunk_text))) as avg_chunk_size,
                    STDDEV(LENGTH(hc.chunk_text)) as size_stddev
                FROM hadis_documents hd
                LEFT JOIN hadis_chunks hc ON hd.id = hc.document_id
                WHERE hc.id IS NOT NULL
                GROUP BY hd.id, hd.filename, hd.kitab_name, hd.total_pages
                HAVING 
                    COUNT(hc.id) > 0 AND (
                        -- Over-chunked: > 3 chunks per page
                        COUNT(hc.id)::decimal / NULLIF(hd.total_pages, 0) > 3.0 OR
                        -- Under-chunked: < 0.3 chunks per page  
                        COUNT(hc.id)::decimal / NULLIF(hd.total_pages, 0) < 0.3 OR
                        -- Chunks terlalu kecil (kurang dari 300 karakter)
                        AVG(LENGTH(hc.chunk_text)) < 300 OR
                        -- Chunks terlalu besar (lebih dari 2000 karakter)
                        AVG(LENGTH(hc.chunk_text)) > 2000 OR
                        -- Variance sangat tinggi (lebih dari 1000)
                        STDDEV(LENGTH(hc.chunk_text)) > 1000
                    )
                ORDER BY ABS(1 - COUNT(hc.id)::decimal / NULLIF(hd.total_pages, 0)) DESC
                LIMIT 10
            """))
            
            inconsistent_docs = result.fetchall()
            
            if not inconsistent_docs:
                print("✅ No inconsistent documents found!")
                return
            
            print(f"Found {len(inconsistent_docs)} documents with chunking issues:")
            for doc in inconsistent_docs:
                print(f"   • ID {doc.id}: {doc.kitab_name}")
                print(f"     Pages: {doc.total_pages}, Chunks: {doc.total_chunks}")
                print(f"     Ratio: {doc.chunks_per_page:.2f}, Avg size: {doc.avg_chunk_size:.0f}")
                print(f"     StdDev: {doc.size_stddev:.0f}")
            
            # 2. Ask for confirmation
            print("\n⚠️  WARNING: This will delete and recreate chunks for selected documents")
            print("   Embeddings will need to be regenerated afterwards")
            
            doc_ids = [doc.id for doc in inconsistent_docs]
            print(f"\n📋 Documents to fix: {doc_ids}")
            
            confirm = input("\n❓ Continue? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y', 'ya']:
                print("❌ Operation cancelled")
                return
            
            # 3. Fix each document
            total_fixed = 0
            for doc in inconsistent_docs:
                analysis = await fixer.analyze_document(db, doc.id)
                if analysis and analysis['issues']:
                    print(f"\n📄 Document ID {doc.id}: {analysis['kitab_name']}")
                    print(f"   Issues: {', '.join(analysis['issues'])}")
                    
                    # Re-chunk
                    new_count = await fixer.rechunk_document(db, doc.id)
                    total_fixed += 1
                    
                    # Verify fix
                    after_analysis = await fixer.analyze_document(db, doc.id)
                    if after_analysis and not after_analysis['issues']:
                        print(f"   ✅ Fixed successfully")
                    else:
                        print(f"   ⚠️  Some issues may remain")
            
            # 4. Summary
            print(f"\n🎉 Fixed {total_fixed} documents")
            
            if total_fixed > 0:
                print("\n🔧 NEXT STEPS:")
                print("   1. Regenerate embeddings for fixed documents:")
                print("      python scripts/regenerate_embeddings.py --doc-ids " + ','.join(map(str, doc_ids[:3])))
                print("   2. Recreate vector indexes:")
                print("      python scripts/create_vector_indexes.py")
                print("   3. Test search quality")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(main())