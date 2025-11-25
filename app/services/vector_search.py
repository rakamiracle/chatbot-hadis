from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chunk import HadisChunk
from typing import List, Dict
from config import settings

class VectorSearch:
    async def search_similar(self, query_embedding: List[float], db: AsyncSession, top_k: int = None) -> List[Dict]:
        """Search dengan re-ranking"""
        if top_k is None:
            top_k = settings.TOP_K_RESULTS * 2  # Ambil lebih banyak untuk re-rank
        
        # Initial retrieval
        query = select(
            HadisChunk,
            (1 - HadisChunk.embedding.cosine_distance(query_embedding)).label("similarity")
        ).order_by(
            HadisChunk.embedding.cosine_distance(query_embedding)
        ).limit(top_k)
        
        result = await db.execute(query)
        rows = result.all()
        
        candidates = []
        for chunk, similarity in rows:
            if similarity >= 0.6:  # Lower threshold untuk re-ranking
                candidates.append({
                    "chunk_id": chunk.id,
                    "text": chunk.chunk_text,
                    "page_number": chunk.page_number,
                    "similarity": float(similarity),
                    "metadata": chunk.chunk_metadata or {}
                })
        
        # Re-rank berdasarkan metadata quality
        ranked = self._rerank(candidates)
        
        # Return top K setelah re-rank
        return ranked[:settings.TOP_K_RESULTS]
    
    def _rerank(self, candidates: List[Dict]) -> List[Dict]:
        """Re-rank berdasarkan quality signals"""
        for candidate in candidates:
            score = candidate['similarity']
            meta = candidate['metadata']
            
            # Boost jika ada metadata lengkap
            if meta.get('nomor_hadis'):
                score += 0.05
            if meta.get('perawi'):
                score += 0.05
            if meta.get('kitab'):
                score += 0.05
            if meta.get('derajat') in ['shahih', 'sahih']:
                score += 0.1
            
            # Boost jika text lebih panjang (lebih informatif)
            text_length = len(candidate['text'])
            if text_length > 500:
                score += 0.03
            
            candidate['final_score'] = min(score, 1.0)
        
        # Sort by final score
        return sorted(candidates, key=lambda x: x['final_score'], reverse=True)