from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chunk import HadisChunk
from app.models.document import HadisDocument
from typing import List, Dict, Optional
from config import settings
import re

class VectorSearch:
    async def search_similar(
        self, 
        query_embedding: List[float],
        query_text: str,
        db: AsyncSession, 
        kitab_filter: Optional[str] = None,
        document_ids: Optional[List[int]] = None,
        top_k: int = None
    ) -> List[Dict]:
        """Hybrid search with optimization"""
        
        if top_k is None:
            top_k = settings.TOP_K_RESULTS * 2  # Reduce from 3x to 2x
        
        # Simplified keyword extraction
        keywords = self._extract_keywords(query_text)
        
        # OPTIMIZATION: Simpler query, less joins
        vector_query = select(
            HadisChunk.id,
            HadisChunk.chunk_text,
            HadisChunk.page_number,
            HadisChunk.chunk_metadata,
            HadisChunk.document_id,
            HadisDocument.kitab_name,
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
            vector_query = vector_query.where(and_(*conditions))
        
        # OPTIMIZATION: Lower threshold for initial retrieval
        vector_query = vector_query.order_by(
            HadisChunk.embedding.cosine_distance(query_embedding)
        ).limit(top_k)
        
        result = await db.execute(vector_query)
        rows = result.all()
        
        candidates = []
        for row in rows:
            similarity = float(row.similarity)
            
            if similarity >= 0.5:  # Lower threshold
                # Quick keyword score
                keyword_score = sum(1 for kw in keywords if kw in row.chunk_text.lower()) / max(len(keywords), 1)
                
                candidates.append({
                    "chunk_id": row.id,
                    "text": row.chunk_text,
                    "page_number": row.page_number,
                    "similarity": similarity,
                    "keyword_score": keyword_score,
                    "metadata": row.chunk_metadata or {},
                    "kitab_name": row.kitab_name,
                    "document_id": row.document_id
                })
        
        # Quick re-rank
        ranked = self._quick_rerank(candidates)
        
        return ranked[:settings.TOP_K_RESULTS]
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords dari query"""
        # Remove stop words
        stop_words = {'apa', 'adalah', 'yang', 'dalam', 'dari', 'dengan', 'untuk', 'pada', 'di', 'ke', 'oleh', 'tentang', 'bagaimana', 'kenapa', 'mengapa', 'siapa', 'kapan', 'dimana'}
        
        # Clean and split
        words = re.findall(r'\w+', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _quick_rerank(self, candidates: List[Dict]) -> List[Dict]:
        """Faster re-ranking"""
        for c in candidates:
            # Simple scoring
            score = (c['similarity'] * 0.7) + (c['keyword_score'] * 0.3)
            
            meta = c['metadata']
            if meta.get('perawi'):
                score += 0.05
            if meta.get('derajat') in ['shahih', 'sahih']:
                score += 0.1
            
            c['final_score'] = min(score, 1.0)
        
        return sorted(candidates, key=lambda x: x['final_score'], reverse=True)