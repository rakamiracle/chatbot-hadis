import asyncio
from sqlalchemy import text
from app.database.connection import get_db

async def diagnostic():
    async for db in get_db():
        print("="*70)
        print("🔍 FULL DATABASE DIAGNOSTIC")
        print("="*70)
        
        # 1. Extension
        r = await db.execute(text("SELECT * FROM pg_extension WHERE extname='vector'"))
        print(f"\n✅ pgvector: {r.fetchone() is not None}")
        
        # 2. Tables
        r = await db.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema='public' ORDER BY table_name
        """))
        tables = [row[0] for row in r.fetchall()]
        print(f"\n📊 Tables ({len(tables)}): {', '.join(tables)}")
        
        # 3. Counts
        r = await db.execute(text("SELECT COUNT(*) FROM hadis_documents"))
        print(f"\n📚 Documents: {r.scalar():,}")
        
        r = await db.execute(text("SELECT COUNT(*) FROM hadis_chunks"))
        print(f"📦 Chunks: {r.scalar():,}")
        
        r = await db.execute(text("SELECT COUNT(*) FROM hadis_chunks WHERE embedding IS NOT NULL"))
        print(f"🔢 Vectors: {r.scalar():,}")
        
        # 4. Index
        r = await db.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename='hadis_chunks' AND indexdef LIKE '%hnsw%'
        """))
        idx = r.fetchone()
        print(f"⚡ HNSW Index: {'✅ ' + idx[0] if idx else '❌ Not found'}")
        
        # 5. Sizes
        r = await db.execute(text("""
            SELECT 
                tablename,
                pg_size_pretty(pg_total_relation_size('public.'||tablename)) as size
            FROM pg_tables
            WHERE schemaname='public'
            ORDER BY pg_total_relation_size('public.'||tablename) DESC
            LIMIT 5
        """))
        print("\n💾 Table Sizes:")
        for row in r.fetchall():
            print(f"   {row[0]}: {row[1]}")
        
        print("\n" + "="*70)
        break

asyncio.run(diagnostic())