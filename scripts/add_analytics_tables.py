"""
Script untuk membuat analytics tables
Jalankan: python scripts/add_analytics_tables.py
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.database.connection import engine, Base
from app.models.analytics import (
    AnalyticsQueryLog, AnalyticsFeedback, AnalyticsPerformance,
    AnalyticsErrorLog, AnalyticsUploadLog
)

async def create_analytics_tables():
    """Create all analytics tables"""
    
    print("🔧 Creating Analytics Tables...")
    print("=" * 60)
    
    async with engine.begin() as conn:
        try:
            # Create all tables from Base metadata
            await conn.run_sync(Base.metadata.create_all)
            
            print("✓ Analytics tables created successfully!")
            print("\nTables created:")
            print("  - analytics_query_log")
            print("  - analytics_feedback")
            print("  - analytics_performance")
            print("  - analytics_error_log")
            print("  - analytics_upload_log")
            
            # Create indexes for better performance
            print("\n🔍 Creating indexes...")
            
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_query_log_session ON analytics_query_log(session_id);",
                "CREATE INDEX IF NOT EXISTS idx_query_log_created ON analytics_query_log(created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_feedback_session ON analytics_feedback(session_id);",
                "CREATE INDEX IF NOT EXISTS idx_feedback_created ON analytics_feedback(created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_error_severity ON analytics_error_log(severity);",
                "CREATE INDEX IF NOT EXISTS idx_error_resolved ON analytics_error_log(resolved);",
                "CREATE INDEX IF NOT EXISTS idx_upload_status ON analytics_upload_log(status);",
            ]
            
            for idx_sql in indexes:
                await conn.execute(text(idx_sql))
            
            print("✓ Indexes created successfully!")
            
            print("\n" + "=" * 60)
            print("🎉 Analytics system ready!")
            print("\nYou can now:")
            print("  1. Track query performance")
            print("  2. Collect user feedback")
            print("  3. Monitor errors")
            print("  4. Analyze usage statistics")
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_analytics_tables())
