from sqlalchemy import select
from app.models.chunk import HadisChunk
from config import settings

class VectorSearch:
    async def search_similar(self, query_embedding, db):
        query = select(
            HadisChunk,
            (1 - HadisChunk.embedding.cosine_distance(query_embedding)).label("similarity")
        ).order_by(HadisChunk.embedding.cosine_distance(query_embedding)).limit(settings.TOP_K_RESULTS)
        
        result = await db.execute(query)
        return [
            {"chunk_id": c.id, "text": c.chunk_text, "page_number": c.page_number, "similarity": float(s)}
            for c, s in result.all() if s >= 0.7
        ]