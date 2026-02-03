#!/usr/bin/env python3
"""
DIAGNOSIS 1: Cek kondisi database hadits
Jalankan: python diagnose_database.py
"""

import sys
import os
import asyncio
from datetime import datetime

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.database.connection import get_db
from sqlalchemy import text

async def diagnose_database():
    """Cek kesehatan database hadits"""
    
    print("🔍 DIAGNOSIS DATABASE HADITS")
    print("=" * 70)
    print("Memeriksa kondisi data dan embeddings...")
    print()
    
    async for db in get_db():
        try:
            # ========== 1. CEK DOKUMEN YANG ADA ==========
            print("1️⃣  📚 DOKUMEN HADITS YANG ADA DI DATABASE")
            print("-" * 50)
            
            result = await db.execute(text("""
                SELECT 
                    id,
                    kitab_name,
                    filename,
                    total_pages,
                    upload_date::date as upload_date,
                    status
                FROM hadis_documents 
                ORDER BY kitab_name
            """))
            
            documents = result.fetchall()
            
            if not documents:
                print("   ❌ TIDAK ADA DOKUMEN DI DATABASE!")
                return
            
            print(f"   ✅ Ditemukan {len(documents)} dokumen hadits:")
            print()
            
            for doc in documents:
                status_icon = "✅" if doc.status == "COMPLETED" else "🔄"
                print(f"   {status_icon} {doc.kitab_name}")
                print(f"      ID: {doc.id} | Halaman: {doc.total_pages:,}")
                print(f"      File: {doc.filename[:40]}...")
                print(f"      Upload: {doc.upload_date}")
                print()
            
            # ========== 2. CEK TOTAL CHUNKS ==========
            print("2️⃣  🧩 TOTAL POTONGAN TEKS (CHUNKS)")
            print("-" * 50)
            
            result = await db.execute(text("""
                SELECT COUNT(*) as total_chunks FROM hadis_chunks
            """))
            total_chunks = result.fetchone().total_chunks
            
            result = await db.execute(text("""
                SELECT COUNT(*) as chunks_with_embeddings 
                FROM hadis_chunks 
                WHERE embedding IS NOT NULL
            """))
            chunks_with_emb = result.fetchone().chunks_with_embeddings
            
            coverage = (chunks_with_emb / total_chunks * 100) if total_chunks > 0 else 0
            
            print(f"   📊 Total chunks: {total_chunks:,}")
            print(f"   ✅ Chunks dengan embeddings: {chunks_with_emb:,}")
            print(f"   📈 Coverage: {coverage:.1f}%")
            print()
            
            if coverage < 95:
                print(f"   ⚠️  PERINGATAN: Coverage kurang dari 95%!")
                print(f"      {total_chunks - chunks_with_emb:,} chunks TIDAK punya embeddings")
                print(f"      Chatbot tidak bisa 'melihat' chunks ini!")
            else:
                print("   ✅ Coverage embeddings mencukupi")
            
            # ========== 3. CEK PER KITAB ==========
            print()
            print("3️⃣  📖 DETAIL PER KITAB")
            print("-" * 50)
            
            result = await db.execute(text("""
                SELECT 
                    hd.kitab_name,
                    COUNT(hc.id) as total_chunks,
                    COUNT(CASE WHEN hc.embedding IS NOT NULL THEN 1 END) as with_embeddings,
                    ROUND(COUNT(CASE WHEN hc.embedding IS NOT NULL THEN 1 END) * 100.0 / COUNT(hc.id), 1) as coverage_percent,
                    ROUND(AVG(LENGTH(hc.chunk_text))) as avg_chunk_size
                FROM hadis_documents hd
                LEFT JOIN hadis_chunks hc ON hd.id = hc.document_id
                GROUP BY hd.id, hd.kitab_name
                ORDER BY coverage_percent ASC, hd.kitab_name
            """))
            
            kitab_stats = result.fetchall()
            
            print("   📋 Kitab dengan coverage terendah:")
            print()
            
            problem_kitabs = []
            for kitab in kitab_stats:
                if kitab.coverage_percent < 100:
                    problem_kitabs.append(kitab)
                
                if kitab.coverage_percent < 90:
                    status = "❌ PROBLEM"
                elif kitab.coverage_percent < 100:
                    status = "⚠️  WARNING"
                else:
                    status = "✅ OK"
                
                print(f"   {status} {kitab.kitab_name}")
                print(f"      Chunks: {kitab.total_chunks:,} | Dengan embeddings: {kitab.with_embeddings:,}")
                print(f"      Coverage: {kitab.coverage_percent}% | Avg size: {kitab.avg_chunk_size:,} chars")
                print()
            
            # ========== 4. CEK UKURAN CHUNKS ==========
            print("4️⃣  📏 ANALISIS UKURAN CHUNKS")
            print("-" * 50)
            
            result = await db.execute(text("""
                SELECT 
                    CASE 
                        WHEN LENGTH(chunk_text) < 100 THEN 'Sangat Pendek (<100)'
                        WHEN LENGTH(chunk_text) < 300 THEN 'Pendek (100-300)'
                        WHEN LENGTH(chunk_text) < 500 THEN 'Agak Pendek (300-500)'
                        WHEN LENGTH(chunk_text) < 1000 THEN 'Optimal (500-1000)'
                        WHEN LENGTH(chunk_text) < 2000 THEN 'Panjang (1000-2000)'
                        ELSE 'Sangat Panjang (>2000)'
                    END as size_category,
                    COUNT(*) as chunk_count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM hadis_chunks), 1) as percentage
                FROM hadis_chunks
                GROUP BY size_category
                ORDER BY chunk_count DESC
            """))
            
            size_stats = result.fetchall()
            
            print("   📊 Distribusi ukuran chunks:")
            print()
            
            optimal_count = 0
            total_chunks_size = 0
            
            for stat in size_stats:
                category = stat.size_category
                count = stat.chunk_count
                percent = stat.percentage
                
                if "Optimal" in category:
                    optimal_count = count
                    status = "✅ OPTIMAL"
                elif "Sangat Pendek" in category or "Sangat Panjang" in category:
                    status = "❌ PROBLEM"
                else:
                    status = "⚠️  WARNING"
                
                print(f"   {status} {category}: {count:,} chunks ({percent}%)")
                total_chunks_size += count
            
            optimal_percent = (optimal_count / total_chunks_size * 100) if total_chunks_size > 0 else 0
            
            print()
            if optimal_percent < 60:
                print(f"   ⚠️  Hanya {optimal_percent:.1f}% chunks berukuran optimal (500-1000 chars)")
                print("      Chunks terlalu pendek/panjang bisa pengaruhi akurasi search")
            else:
                print(f"   ✅ {optimal_percent:.1f}% chunks berukuran optimal")
            
            # ========== 5. CEK INDEXES ==========
            print()
            print("5️⃣  🔍 CEK INDEX UNTUK PENCARIAN CEPAT")
            print("-" * 50)
            
            result = await db.execute(text("""
                SELECT 
                    indexname,
                    tablename,
                    indexdef
                FROM pg_indexes
                WHERE tablename IN ('hadis_chunks', 'hadis_documents')
                AND indexdef LIKE '%vector%' OR indexdef LIKE '%hnsw%' OR indexdef LIKE '%ivfflat%'
                ORDER BY tablename, indexname
            """))
            
            vector_indexes = result.fetchall()
            
            if vector_indexes:
                print(f"   ✅ Ditemukan {len(vector_indexes)} vector index:")
                print()
                for idx in vector_indexes:
                    print(f"   📌 {idx.indexname} pada {idx.tablename}")
                    
                    # Cek tipe index
                    if 'hnsw' in idx.indexdef.lower():
                        print(f"      Type: HNSW (cepat untuk data besar)")
                    elif 'ivfflat' in idx.indexdef.lower():
                        print(f"      Type: IVFFLAT (cepat untuk data kecil)")
                    else:
                        print(f"      Type: Unknown")
                    
                    # Extract parameters jika ada
                    import re
                    params = re.findall(r"WITH\s*\((.*?)\)", idx.indexdef)
                    if params:
                        print(f"      Parameters: {params[0]}")
                    print()
            else:
                print("   ❌ TIDAK ADA VECTOR INDEX!")
                print("      Pencarian akan SANGAT LAMBAT untuk 100k+ chunks")
            
            # ========== 6. REKOMENDASI ==========
            print("=" * 70)
            print("🎯 REKOMENDASI PERBAIKAN")
            print("=" * 70)
            
            recommendations = []
            
            # Rekomendasi berdasarkan masalah
            if coverage < 95:
                recommendations.append({
                    "priority": "🚨 HIGH",
                    "action": "Regenerate missing embeddings",
                    "reason": f"{total_chunks - chunks_with_emb:,} chunks tanpa embeddings",
                    "script": "python regenerate_embeddings.py"
                })
            
            if optimal_percent < 60:
                recommendations.append({
                    "priority": "⚠️  MEDIUM", 
                    "action": "Optimize chunk sizes",
                    "reason": f"Hanya {optimal_percent:.1f}% chunks berukuran optimal",
                    "script": "python optimize_chunk_sizes.py"
                })
            
            if not vector_indexes:
                recommendations.append({
                    "priority": "🚨 HIGH",
                    "action": "Create HNSW index",
                    "reason": "Tidak ada index untuk pencarian cepat",
                    "script": "python create_hnsw_index.py"
                })
            
            if len(problem_kitabs) > 0:
                recommendations.append({
                    "priority": "⚠️  MEDIUM",
                    "action": "Fix problematic kitabs",
                    "reason": f"{len(problem_kitabs)} kitab dengan coverage < 100%",
                    "script": "python fix_kitab_embeddings.py"
                })
            
            # Tampilkan rekomendasi
            if not recommendations:
                print("   ✅ Database dalam kondisi BAIK!")
                print("   Tidak perlu perbaikan mendesak")
            else:
                print(f"   Ditemukan {len(recommendations)} masalah yang perlu diperbaiki:")
                print()
                
                for i, rec in enumerate(recommendations, 1):
                    print(f"   {i}. [{rec['priority']}] {rec['action']}")
                    print(f"      Alasan: {rec['reason']}")
                    print(f"      Script: {rec['script']}")
                    print()
            
            # ========== 7. SUMMARY ==========
            print("=" * 70)
            print("📊 SUMMARY DIAGNOSIS")
            print("=" * 70)
            
            summary_stats = [
                ("Total Dokumen", len(documents)),
                ("Total Chunks", f"{total_chunks:,}"),
                ("Coverage Embeddings", f"{coverage:.1f}%"),
                ("Chunks Optimal Size", f"{optimal_percent:.1f}%"),
                ("Vector Indexes", len(vector_indexes)),
                ("Kitab Bermasalah", len(problem_kitabs))
            ]
            
            for label, value in summary_stats:
                print(f"   {label:25} : {value}")
            
            print()
            print("⏰ Diagnosis selesai pada:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(diagnose_database())