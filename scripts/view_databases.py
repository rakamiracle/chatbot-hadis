"""
Script untuk melihat database PostgreSQL dan MySQL
Jalankan: python scripts/view_databases.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False

from sqlalchemy import text
from app.database.connection import engine

# Konfigurasi MySQL (sesuai dengan import_from_mysql.py)
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root12345678",
    "database": "hadis_kating",
}

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

async def view_postgresql():
    """View PostgreSQL database structure"""
    print_header("📊 DATABASE POSTGRESQL")
    
    async with engine.begin() as conn:
        try:
            # Get all tables
            result = await conn.execute(text("""
                SELECT 
                    schemaname, 
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """))
            
            tables = result.fetchall()
            
            if not tables:                print("\n❌ No tables found!")
                return
            
            print(f"\n✓ Found {len(tables)} table(s):\n")
            print(f"{'No':<5} {'Table Name':<40} {'Size':<15}")
            print("-" * 80)
            
            for idx, (schema, table_name, size) in enumerate(tables, 1):
                print(f"{idx:<5} {table_name:<40} {size:<15}")
            
            # Get total row counts
            print("\n" + "-" * 80)
            print(f"{'Table Name':<40} {'Row Count':<15}")
            print("-" * 80)
            
            for _, table_name, _ in tables:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
                count = result.scalar()
                print(f"{table_name:<40} {count:>10,}")
            
            # Database size
            result = await conn.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size;
            """))
            db_size = result.scalar()
            print("\n" + "-" * 80)
            print(f"Total Database Size: {db_size}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            await engine.dispose()

def view_mysql():
    """View MySQL database structure"""
    print_header("📊 DATABASE MYSQL (hadis_kating)")
    
    if not PYMYSQL_AVAILABLE:
        print("\n❌ pymysql not installed!")
        print("💡 Install: pip install pymysql")
        return
    
    try:
        # Connect to MySQL
        print("\n🔌 Connecting to MySQL...")
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        print("   ✓ Connected!\n")
        
        # Get all tables
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        
        if not tables:
            print("❌ No tables found!")
            return
        
        table_list = [list(t.values())[0] for t in tables]
        
        print(f"✓ Found {len(table_list)} table(s):\n")
        print(f"{'No':<5} {'Table Name':<40} {'Row Count':<15}")
        print("-" * 80)
        
        for idx, table_name in enumerate(table_list, 1):
            cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`;")
            count = cursor.fetchone()['count']
            print(f"{idx:<5} {table_name:<40} {count:>10,}")
        
        # Database size
        cursor.execute(f"""
            SELECT 
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
            FROM information_schema.TABLES
            WHERE table_schema = '{MYSQL_CONFIG['database']}';
        """)
        size = cursor.fetchone()['size_mb']
        print("\n" + "-" * 80)
        print(f"Total Database Size: {size} MB")
        
        cursor.close()
        conn.close()
        
    except pymysql.err.OperationalError as e:
        print(f"\n❌ Cannot connect to MySQL: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Pastikan MySQL server running")
        print("   - Cek kredensial di MYSQL_CONFIG")
        print(f"   - Host: {MYSQL_CONFIG['host']}")
        print(f"   - User: {MYSQL_CONFIG['user']}")
        print(f"   - Database: {MYSQL_CONFIG['database']}")
    except Exception as e:
        print(f"\n❌ Error: {e}")

async def main():
    """Main function"""
    print("\n" + "🔍 DATABASE VIEWER")
    print("=" * 80)
    
    # View PostgreSQL
    await view_postgresql()
    
    # View MySQL
    view_mysql()
    
    print("\n" + "=" * 80)
    print("✓ Database viewing complete!")
    print("\n💡 Untuk melihat struktur detail tabel tertentu:")
    print("   PostgreSQL: \\d nama_tabel (dalam psql)")
    print("   MySQL: DESCRIBE nama_tabel; (dalam mysql client)")
    print()

if __name__ == "__main__":
    asyncio.run(main())
  