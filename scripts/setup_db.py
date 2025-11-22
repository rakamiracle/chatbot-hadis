import asyncio
import sys
sys.path.append('.')

from app.database.connection import engine, Base
from app.models.document import HadisDocument
from app.models.chunk import HadisChunk
from app.models.chat_history import ChatHistory

async def setup_database():
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database setup completed!")

if __name__ == "__main__":
    asyncio.run(setup_database())