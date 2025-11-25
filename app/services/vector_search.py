from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chunk import HadisChunk
from app.models.document import HadisDocument
from typing import List, Dict, Optional
from config import settings

class VectorSearch:
    async def search_similar(
        self, 
        query_embedding: List[float], 
        db: AsyncSession, 
        kitab_filter: Optional[str] = None,
        document_ids: Optional[List[int]] = None,
        top_k: int = None
    ) -> List[Dict]:
        """Search dengan filter kitab/dokumen"""
        
        if top_k is None:
            top_k = settings.TOP_K_RESULTS * 2
        
        # Build query dengan join ke documents
        query = select(
            HadisChunk,
            HadisDocument,
            (1 - HadisChunk.embedding.cosine_distance(query_embedding)).label("similarity")
        ).join(
            HadisDocument, HadisChunk.document_id == HadisDocument.id
        )
        
        # Apply filters
        conditions = []
        
        if kitab_filter:
            conditions.append(HadisDocument.kitab_name.ilike(f"%{kitab_filter}%"))
        
        if document_ids:
            conditions.append(HadisChunk.document_id.in_(document_ids))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(
            HadisChunk.embedding.cosine_distance(query_embedding)
        ).limit(top_k)
        
        result = await db.execute(query)
        rows = result.all()
        
        candidates = []
        for chunk, doc, similarity in rows:
            if similarity >= 0.6:
                candidates.append({
                    "chunk_id": chunk.id,
                    "text": chunk.chunk_text,
                    "page_number": chunk.page_number,
                    "similarity": float(similarity),
                    "metadata": chunk.chunk_metadata or {},
                    "kitab_name": doc.kitab_name,
                    "document_id": doc.id
                })
        
        ranked = self._rerank(candidates)
        return ranked[:settings.TOP_K_RESULTS]
    
    def _rerank(self, candidates: List[Dict]) -> List[Dict]:
        """Re-rank berdasarkan quality signals"""
        for candidate in candidates:
            score = candidate['similarity']
            meta = candidate['metadata']
            
            if meta.get('nomor_hadis'):
                score += 0.05
            if meta.get('perawi'):
                score += 0.05
            if meta.get('kitab'):
                score += 0.05
            if meta.get('derajat') in ['shahih', 'sahih']:
                score += 0.1
            
            text_length = len(candidate['text'])
            if text_length > 500:
                score += 0.03
            
            candidate['final_score'] = min(score, 1.0)
        
        return sorted(candidates, key=lambda x: x['final_score'], reverse=True)