
import asyncio
import sys
import os

# Add the project root to sys.path to allow imports from app
sys.path.append(os.getcwd())

from app.services.embedding_service import EmbeddingService

async def main():
    try:
        print("Initializing EmbeddingService...")
        embed = EmbeddingService()
        print("Generating embedding for 'test hadis'...")
        result = await embed.generate_embedding("test hadis")
        print("-" * 50)
        print(f"Dimension: {len(result)}")
        print(f"Sample (first 10): {result[:10]}")
        print("-" * 50)
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
