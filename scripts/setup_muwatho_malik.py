import asyncio
from app.database.connection import engine, Base

async def setup_database():
    """Buat semua tabel di database"""
    
    print("=" * 70)
    print("🔧 SETUP DATABASE MUWATHO MALIK")
    print("=" * 70)
    
    try:
        # Import models untuk ensure mereka di-register
        from app.models.hadis import Kitab, Bab, Hadis
        
        print("\n1️⃣ Creating tables...")
        
        # Buat semua tabel berdasarkan models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("   ✅ Tables created successfully!")
        
        print("\n2️⃣ Inserting reference data...")
        
        from app.database.connection import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            # Cek apakah data sudah ada
            from sqlalchemy import select, func
            
            kitab_count = await db.execute(select(func.count()).select_from(Kitab))
            if kitab_count.scalar() > 0:
                print("   ⚠️  Reference data sudah ada, skip insert")
                return
            
            # Insert data kitab
            kitab_list = [
                Kitab(id=1, nama_kitab="Musnad Ahmad"),
                Kitab(id=2, nama_kitab="Musnad Darimi"),
                Kitab(id=3, nama_kitab="Muwatho Malik"),
                Kitab(id=4, nama_kitab="Shahih Bukhari"),
                Kitab(id=5, nama_kitab="Shahih Muslim"),
                Kitab(id=6, nama_kitab="Sunan Abu Daud"),
                Kitab(id=7, nama_kitab="Sunan Ibnu Majah"),
                Kitab(id=8, nama_kitab="Sunan Nasai"),
                Kitab(id=9, nama_kitab="Sunan Tirmidzi"),
                Kitab(id=10, nama_kitab="Riyadhus Shalihin"),
                Kitab(id=11, nama_kitab="Musnad Syafi'i"),
            ]
            
            for k in kitab_list:
                db.add(k)
            
            # Insert data bab
            bab = Bab(id=27, Bab="Waktu-Waktu Shalat")
            db.add(bab)
            
            await db.commit()
            
            print("   ✅ Reference data inserted!")
        
        print("\n" + "=" * 70)
        print("✅ DATABASE SETUP BERHASIL!")
        print("=" * 70)
        print("\nNext step: python scripts/insert_hadis.py")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == "__main__":=
    asyncio.run(setup_database())