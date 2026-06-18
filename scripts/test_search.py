import asyncio
from app.database.connection import get_db
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import VectorSearch

async def test():
    embed = EmbeddingService()
    search = VectorSearch()
    
    query = "Apa itu wudhu?"
    print(f"Query: {query}\n")
    
    qemb = await embed.generate_embedding(query)
    
    async for db in get_db():
        results = await search.search_similar(qemb, query, db, top_k=5)
        
        for i, r in enumerate(results, 1):
            print(f"{i}. Score: {r['similarity']:.3f}")
            print(f"   {r['text'][:100]}...\n")
        break

asyncio.run(test())