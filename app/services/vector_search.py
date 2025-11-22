from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chunk import HadisChunk
from typing import List, Dict
from config import settings

class VectorSearch:
    async def search_similar(self, query_embedding: List[float], db: AsyncSession) -> List[Dict]:
        # Cosine similarity search
        query = select(
            HadisChunk,
            (1 - HadisChunk.embedding.cosine_distance(query_embedding)).label("similarity")
        ).order_by(
            HadisChunk.embedding.cosine_distance(query_embedding)
        ).limit(settings.TOP_K_RESULTS)
        
        result = await db.execute(query)
        rows = result.all()
        
        results = []
        for chunk, similarity in rows:
            if similarity >= settings.SIMILARITY_THRESHOLD:
                results.append({
                    "chunk_id": chunk.id,
                    "text": chunk.chunk_text,
                    "page_number": chunk.page_number,
                    "similarity": float(similarity),
                    "metadata": chunk.metadata
                })
        
        return results