#!/usr/bin/env python3
"""
OPTIMIZE CHUNK SIZES - Fix untuk ukuran chunks tidak optimal
Jalankan: python optimize_chunk_sizes.py --doc-id 8
"""

import sys
import os
import asyncio
import re
from typing import List, Tuple, Dict

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.database.connection import get_db
from sqlalchemy import text

class ChunkOptimizer:
    def __init__(self):
        # Target: 500-1000 karakter per chunk
        self.target_min = 500
        self.target_max = 1000
        self.overlap_chars = 50  # Overlap antar chunks
    
    async def analyze_document(self, doc_id: int) -> Dict:
        """Analisis chunk sizes untuk dokumen tertentu"""
        async for db in get_db():
            result = await db.execute(text("""
                SELECT 
                    hd.kitab_name,
                    hd.filename,
                    COUNT(hc.id) as total_chunks,
                    AVG(LENGTH(hc.chunk_text)) as avg_size,
                    MIN(LENGTH(hc.chunk_text)) as min_size,
                    MAX(LENGTH(hc.chunk_text)) as max_size,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY LENGTH(hc.chunk_text)) as p25,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY LENGTH(hc.chunk_text)) as median,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY LENGTH(hc.chunk_text)) as p75
                FROM hadis_documents hd
                JOIN hadis_chunks hc ON hd.id = hc.document_id
                WHERE hd.id = :doc_id
                GROUP BY hd.id, hd.kitab_name, hd.filename
            """), {"doc_id": doc_id})
            
            return result.fetchone()
    
    def split_large_chunk(self, text: str, page_num: int) -> List[Tuple[str, int]]:
        """Split chunk yang terlalu besar (> target_max)"""
        if len(text) <= self.target_max:
            return [(text, page_num)]
        
        chunks = []
        current_pos = 0
        
        # Coba split by kalimat dulu
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sent_size = len(sentence)
            
            if current_size + sent_size > self.target_max and current_chunk:
                # Finalize current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append((chunk_text, page_num))
                
                # Start new chunk dengan overlap
                overlap_text = ' '.join(current_chunk[-3:]) if len(current_chunk) >= 3 else chunk_text[-100:]
                current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                current_size = len(' '.join(current_chunk))
            else:
                current_chunk.append(sentence)
                current_size += sent_size + 1  # +1 untuk spasi
        
        # Add last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append((chunk_text, page_num))
        
        return chunks
    
    def merge_small_chunks(self, chunks_data: List[Tuple[str, int, int]]) -> List[Tuple[str, int]]:
        """Merge chunks yang terlalu kecil (< target_min)"""
        if not chunks_data:
            return []
        
        # Group by page
        page_chunks = {}
        for chunk_text, page_num, chunk_id in chunks_data:
            if page_num not in page_chunks:
                page_chunks[page_num] = []
            page_chunks[page_num].append((chunk_text, chunk_id))
        
        merged_chunks = []
        
        for page_num, chunks in page_chunks.items():
            if len(chunks) == 1:
                # Single chunk, check if needs merging with next page
                merged_chunks.append((chunks[0][0], page_num))
                continue
            
            # Merge chunks on same page
            current_text = []
            current_size = 0
            
            for chunk_text, chunk_id in chunks:
                chunk_size = len(chunk_text)
                
                if current_size + chunk_size <= self.target_max:
                    current_text.append(chunk_text)
                    current_size += chunk_size
                else:
                    # Finalize current merged chunk
                    if current_text:
                        merged_text = ' '.join(current_text)
                        merged_chunks.append((merged_text, page_num))
                    
                    # Start new
                    current_text = [chunk_text]
                    current_size = chunk_size
            
            # Add last merged chunk
            if current_text:
                merged_text = ' '.join(current_text)
                merged_chunks.append((merged_text, page_num))
        
        return merged_chunks
    
    async def optimize_document(self, doc_id: int) -> Dict:
        """Optimize chunk sizes untuk satu dokumen"""
        print(f"\n🔧 Optimizing document ID {doc_id}...")
        
        async for db in get_db():
            try:
                # 1. Backup chunks dulu
                print("   📦 Creating backup...")
                await db.execute(text("""
                    CREATE TABLE IF NOT EXISTS backup_chunks_optimize AS 
                    SELECT * FROM hadis_chunks WHERE document_id = :doc_id
                """), {"doc_id": doc_id})
                
                # 2. Get all chunks untuk dokumen ini
                result = await db.execute(text("""
                    SELECT id, page_number, chunk_text, chunk_index
                    FROM hadis_chunks 
                    WHERE document_id = :doc_id
                    ORDER BY page_number, chunk_index
                """), {"doc_id": doc_id})
                
                chunks = result.fetchall()
                print(f"   📊 Found {len(chunks)} chunks")
                
                if len(chunks) == 0:
                    print("   ⚠️  No chunks found for this document")
                    return {"status": "no_chunks", "processed": 0}
                
                # 3. Kategorikan chunks
                small_chunks = []  # < target_min
                large_chunks = []  # > target_max
                optimal_chunks = []  # target_min <= size <= target_max
                
                for chunk in chunks:
                    chunk_size = len(chunk.chunk_text)
                    
                    if chunk_size < self.target_min:
                        small_chunks.append((chunk.chunk_text, chunk.page_number, chunk.id))
                    elif chunk_size > self.target_max:
                        large_chunks.append((chunk.chunk_text, chunk.page_number, chunk.id))
                    else:
                        optimal_chunks.append((chunk.chunk_text, chunk.page_number, chunk.id))
                
                print(f"   📈 Analysis:")
                print(f"      • Optimal chunks: {len(optimal_chunks)}")
                print(f"      • Too small (<{self.target_min}): {len(small_chunks)}")
                print(f"      • Too large (>{self.target_max}): {len(large_chunks)}")
                
                # 4. Process large chunks (split them)
                new_chunks_from_large = []
                for chunk_text, page_num, chunk_id in large_chunks:
                    split_results = self.split_large_chunk(chunk_text, page_num)
                    new_chunks_from_large.extend(split_results)
                
                # 5. Process small chunks (merge them)
                merged_chunks = self.merge_small_chunks(small_chunks)
                
                # 6. Combine all chunks
                all_new_chunks = []
                
                # Add optimal chunks as-is
                for chunk_text, page_num, chunk_id in optimal_chunks:
                    all_new_chunks.append((chunk_text, page_num))
                
                # Add split large chunks
                all_new_chunks.extend(new_chunks_from_large)
                
                # Add merged small chunks
                all_new_chunks.extend(merged_chunks)
                
                # Sort by page number
                all_new_chunks.sort(key=lambda x: x[1])
                
                print(f"   🔄 After optimization:")
                print(f"      • Total new chunks: {len(all_new_chunks)}")
                print(f"      • Reduction: {len(chunks) - len(all_new_chunks)} chunks")
                
                # 7. Delete old chunks and insert new ones
                print("   🗑️  Deleting old chunks...")
                await db.execute(text("DELETE FROM hadis_chunks WHERE document_id = :doc_id"), 
                               {"doc_id": doc_id})
                
                print("   📝 Inserting optimized chunks...")
                
                for idx, (chunk_text, page_num) in enumerate(all_new_chunks):
                    await db.execute(text("""
                        INSERT INTO hadis_chunks 
                        (document_id, page_number, chunk_text, chunk_index)
                        VALUES (:doc_id, :page_num, :chunk_text, :chunk_idx)
                    """), {
                        "doc_id": doc_id,
                        "page_num": page_num,
                        "chunk_text": chunk_text,
                        "chunk_idx": idx
                    })
                
                # 8. Clear embeddings (need to regenerate)
                print("   🧹 Clearing old embeddings...")
                await db.execute(text("""
                    UPDATE hadis_chunks 
                    SET embedding = NULL
                    WHERE document_id = :doc_id
                """), {"doc_id": doc_id})
                
                await db.commit()
                
                # 9. Verify
                result = await db.execute(text("""
                    SELECT 
                        COUNT(*) as new_count,
                        AVG(LENGTH(chunk_text)) as new_avg_size,
                        MIN(LENGTH(chunk_text)) as new_min_size,
                        MAX(LENGTH(chunk_text)) as new_max_size
                    FROM hadis_chunks
                    WHERE document_id = :doc_id
                """), {"doc_id": doc_id})
                
                new_stats = result.fetchone()
                
                print(f"   ✅ Optimization complete!")
                print(f"      New chunks: {new_stats.new_count}")
                print(f"      New avg size: {new_stats.new_avg_size:.0f} chars")
                print(f"      Size range: {new_stats.new_min_size} - {new_stats.new_max_size} chars")
                
                return {
                    "status": "success",
                    "processed": len(all_new_chunks),
                    "old_count": len(chunks),
                    "new_count": new_stats.new_count,
                    "reduction": len(chunks) - new_stats.new_count,
                    "new_avg_size": new_stats.new_avg_size
                }
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                await db.rollback()
                return {"status": "error", "message": str(e)}
    
    async def analyze_all_documents(self):
        """Analisis semua dokumen untuk rekomendasi"""
        print("\n🔍 ANALYZING ALL DOCUMENTS FOR OPTIMIZATION")
        print("=" * 60)
        
        async for db in get_db():
            result = await db.execute(text("""
                SELECT 
                    hd.id,
                    hd.kitab_name,
                    COUNT(hc.id) as total_chunks,
                    AVG(LENGTH(hc.chunk_text)) as avg_size,
                    COUNT(CASE WHEN LENGTH(hc.chunk_text) < 500 THEN 1 END) as too_small,
                    COUNT(CASE WHEN LENGTH(hc.chunk_text) > 1000 THEN 1 END) as too_large,
                    COUNT(CASE WHEN LENGTH(hc.chunk_text) BETWEEN 500 AND 1000 THEN 1 END) as optimal
                FROM hadis_documents hd
                JOIN hadis_chunks hc ON hd.id = hc.document_id
                GROUP BY hd.id, hd.kitab_name
                ORDER BY (COUNT(CASE WHEN LENGTH(hc.chunk_text) < 500 THEN 1 END) + 
                         COUNT(CASE WHEN LENGTH(hc.chunk_text) > 1000 THEN 1 END)) DESC
            """))
            
            all_docs = result.fetchall()
            
            print("\n📋 PRIORITAS OPTIMIZATION:")
            print("ID  | Kitab Name                    | Chunks | Avg Size | Too Small | Too Large | Optimal %")
            print("-" * 90)
            
            priority_list = []
            
            for doc in all_docs:
                optimal_percent = (doc.optimal / doc.total_chunks * 100) if doc.total_chunks > 0 else 0
                
                # Tentukan priority
                if optimal_percent < 50:
                    priority = "🚨 HIGH"
                elif optimal_percent < 70:
                    priority = "⚠️  MEDIUM"
                else:
                    priority = "✅ LOW"
                
                print(f"{doc.id:3d} | {doc.kitab_name:30} | {doc.total_chunks:6d} | {doc.avg_size:8.0f} | {doc.too_small:9d} | {doc.too_large:9d} | {optimal_percent:7.1f}% {priority}")
                
                if optimal_percent < 70:
                    priority_list.append({
                        "id": doc.id,
                        "kitab_name": doc.kitab_name,
                        "priority": priority,
                        "optimal_percent": optimal_percent
                    })
            
            return priority_list

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimize chunk sizes for better search accuracy")
    parser.add_argument("--doc-id", type=int, help="Optimize single document by ID")
    parser.add_argument("--doc-ids", help="Optimize multiple documents (comma-separated)")
    parser.add_argument("--analyze", action="store_true", help="Analyze all documents only")
    parser.add_argument("--optimize-all", action="store_true", help="Optimize all problematic documents")
    
    args = parser.parse_args()
    
    optimizer = ChunkOptimizer()
    
    if args.analyze:
        # Hanya analisis
        await optimizer.analyze_all_documents()
        
    elif args.doc_id:
        # Optimize single document
        doc_info = await optimizer.analyze_document(args.doc_id)
        if doc_info:
            print(f"\n📄 Document: {doc_info.kitab_name}")
            print(f"   Current chunks: {doc_info.total_chunks}")
            print(f"   Current avg size: {doc_info.avg_size:.0f} chars")
            print(f"   Size range: {doc_info.min_size} - {doc_info.max_size} chars")
            
            confirm = input(f"\n❓ Optimize document {args.doc_id}? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y', 'ya']:
                result = await optimizer.optimize_document(args.doc_id)
                
                if result["status"] == "success":
                    print(f"\n🎉 Successfully optimized!")
                    print(f"   Next: Regenerate embeddings for document {args.doc_id}")
                    print(f"   Run: python scripts/regenerate_embeddings.py --doc-ids {args.doc_id}")
            else:
                print("❌ Operation cancelled")
    
    elif args.doc_ids:
        # Optimize multiple documents
        doc_ids = [int(id.strip()) for id in args.doc_ids.split(",")]
        
        print(f"🔄 Optimizing {len(doc_ids)} documents: {doc_ids}")
        
        for doc_id in doc_ids:
            print(f"\n{'='*50}")
            result = await optimizer.optimize_document(doc_id)
            
            if result["status"] == "success":
                print(f"✅ Document {doc_id} optimized successfully")
            else:
                print(f"❌ Failed to optimize document {doc_id}")
        
        print(f"\n🎉 All documents optimized!")
        print(f"📋 Documents done: {doc_ids}")
        print(f"\n🔧 Next: Regenerate embeddings")
        print(f"   Run: python scripts/regenerate_embeddings.py --doc-ids {args.doc_ids}")
    
    elif args.optimize_all:
        # Optimize all problematic documents
        priority_list = await optimizer.analyze_all_documents()
        
        problematic = [doc for doc in priority_list if doc["optimal_percent"] < 70]
        
        if not problematic:
            print("\n✅ All documents already have optimal chunk sizes!")
            return
        
        print(f"\n🔧 Found {len(problematic)} documents needing optimization:")
        for doc in problematic:
            print(f"   • ID {doc['id']}: {doc['kitab_name']} ({doc['optimal_percent']:.1f}% optimal)")
        
        confirm = input(f"\n❓ Optimize all {len(problematic)} documents? (yes/no): ").strip().lower()
        
        if confirm in ['yes', 'y', 'ya']:
            for doc in problematic:
                print(f"\n{'='*50}")
                print(f"Optimizing ID {doc['id']}: {doc['kitab_name']}")
                await optimizer.optimize_document(doc["id"])
            
            doc_ids_str = ','.join(str(doc["id"]) for doc in problematic)
            print(f"\n🎉 All documents optimized!")
            print(f"\n🔧 Next: Regenerate embeddings")
            print(f"   Run: python scripts/regenerate_embeddings.py --doc-ids {doc_ids_str}")
        else:
            print("❌ Operation cancelled")
    
    else:
        # Default: show analysis
        print("🔧 CHUNK SIZE OPTIMIZER")
        print("=" * 60)
        print("\nUsage options:")
        print("  1. python optimize_chunk_sizes.py --analyze")
        print("     → Analyze all documents (no changes)")
        print("\n  2. python optimize_chunk_sizes.py --doc-id 8")
        print("     → Optimize single document (ID 8)")
        print("\n  3. python optimize_chunk_sizes.py --doc-ids 8,16,17")
        print("     → Optimize multiple documents")
        print("\n  4. python optimize_chunk_sizes.py --optimize-all")
        print("     → Optimize ALL problematic documents")
        print("\n📊 Based on diagnosis, recommended action:")
        print("   python optimize_chunk_sizes.py --doc-ids 8,16,17")

if __name__ == "__main__":
    asyncio.run(main())