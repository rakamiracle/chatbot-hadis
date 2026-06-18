"""
Script untuk melihat struktur tabel analytics di database
Jalankan: python scripts/view_analytics_tables.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, inspect
from app.database.connection import engine

async def view_analytics_tables():
    """View all analytics tables and their structure"""
    
    print("📊 Analytics Tables - Database Structure")
    print("=" * 80)
    
    async with engine.begin() as conn:
        try:
            # Get list of all tables starting with 'analytics_'
            
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'analytics_%'
                ORDER BY table_name;
            """))
            
            tables = result.fetchall()
            
            if not tables:
                print("❌ No analytics tables found!")
                print("💡 Run: python scripts/add_analytics_tables.py")
                return
            
            print(f"\n✓ Found {len(tables)} analytics table(s):\n")
            
            for idx, (table_name,) in enumerate(tables, 1):
                print(f"{idx}. {table_name}")
            
            print("\n" + "=" * 80)
            
            # Show detailed structure for each table
            for (table_name,) in tables:
                print(f"\n📋 Table: {table_name}")
                print("-" * 80)
                
                # Get column information
                result = await conn.execute(text(f"""
                    SELECT 
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position;
                """))
                
                columns = result.fetchall()
                
                print(f"\n{'Column Name':<30} {'Type':<20} {'Nullable':<10} {'Default':<20}")
                print("-" * 80)
                
                for col_name, data_type, max_length, nullable, default in columns:
                    # Format data type with length if applicable
                    if max_length:
                        type_str = f"{data_type}({max_length})"
                    else:
                        type_str = data_type
                    
                    # Shorten default value if too long
                    default_str = str(default) if default else '-'
                    if len(default_str) > 20:
                        default_str = default_str[:17] + '...'
                    
                    print(f"{col_name:<30} {type_str:<20} {nullable:<10} {default_str:<20}")
                
                # Get indexes
                result = await conn.execute(text(f"""
                    SELECT 
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE tablename = '{table_name}'
                    ORDER BY indexname;
                """))
                
                indexes = result.fetchall()
                
                if indexes:
                    print(f"\n🔍 Indexes ({len(indexes)}):")
                    for idx_name, idx_def in indexes:
                        print(f"  - {idx_name}")
                
                # Get row count
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
                count = result.scalar()
                print(f"\n📊 Total Records: {count}")
                
                print()
            
            print("=" * 80)
            print("✓ Table structure view complete!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(view_analytics_tables())
