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
        query_text: str,  # Tambah raw query text
        db: AsyncSession, 
        kitab_filter: Optional[str] = None,
        document_ids: Optional[List[int]] = None,
        top_k: int = None
    ) -> List[Dict]:
        """Hybrid search: Vector + Keyword"""
        
        if top_k is None:
            top_k = settings.TOP_K_RESULTS * 3  # Ambil lebih banyak untuk re-rank
        
        # Extract keywords dari query
        keywords = self._extract_keywords(query_text)
        
        # Vector search
        vector_query = select(
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
            vector_query = vector_query.where(and_(*conditions))
        
        vector_query = vector_query.order_by(
            HadisChunk.embedding.cosine_distance(query_embedding)
        ).limit(top_k)
        
        result = await db.execute(vector_query)
        rows = result.all()
        
        candidates = []
        for chunk, doc, similarity in rows:
            if similarity >= 0.55:  # Lower threshold
                # Keyword matching score
                keyword_score = self._calculate_keyword_score(chunk.chunk_text, keywords)
                
                candidates.append({
                    "chunk_id": chunk.id,
                    "text": chunk.chunk_text,
                    "page_number": chunk.page_number,
                    "similarity": float(similarity),
                    "keyword_score": keyword_score,
                    "metadata": chunk.chunk_metadata or {},
                    "kitab_name": doc.kitab_name,
                    "document_id": doc.id
                })
        
        # Re-rank dengan hybrid score
        ranked = self._hybrid_rerank(candidates, query_text)
        
        return ranked[:settings.TOP_K_RESULTS]
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords dari query"""
        # Remove stop words
        stop_words = {'apa', 'adalah', 'yang', 'dalam', 'dari', 'dengan', 'untuk', 'pada', 'di', 'ke', 'oleh', 'tentang', 'bagaimana', 'kenapa', 'mengapa', 'siapa', 'kapan', 'dimana'}
        
        # Clean and split
        words = re.findall(r'\w+', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """Calculate keyword matching score"""
        if not keywords:
            return 0.0
        
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        
        return matches / len(keywords)
    
    def _hybrid_rerank(self, candidates: List[Dict], query: str) -> List[Dict]:
        """Hybrid re-ranking: Vector + Keyword + Metadata + Query-specific"""
        
        for candidate in candidates:
            vector_score = candidate['similarity']
            keyword_score = candidate['keyword_score']
            meta = candidate['metadata']
            text = candidate['text']
            
            # Base score: 70% vector + 30% keyword
            base_score = (vector_score * 0.7) + (keyword_score * 0.3)
            
            # Metadata boosts
            if meta.get('nomor_hadis'):
                base_score += 0.05
            if meta.get('perawi'):
                base_score += 0.05
            if meta.get('kitab'):
                base_score += 0.05
            if meta.get('derajat') in ['shahih', 'sahih']:
                base_score += 0.1
            
            # Query-specific boosts
            query_lower = query.lower()
            
            # Boost jika query mention perawi dan chunk ada perawi yang sama
            if 'bukhari' in query_lower and meta.get('perawi', '').lower() == 'bukhari':
                base_score += 0.15
            if 'muslim' in query_lower and meta.get('perawi', '').lower() == 'muslim':
                base_score += 0.15
            
            # Boost untuk text yang lebih lengkap
            text_length = len(text)
            if text_length > 500:
                base_score += 0.05
            elif text_length < 200:
                base_score -= 0.05
            
            # Boost jika ada exact phrase match
            if any(phrase in text.lower() for phrase in self._extract_phrases(query)):
                base_score += 0.1
            
            candidate['final_score'] = min(base_score, 1.0)
        
        return sorted(candidates, key=lambda x: x['final_score'], reverse=True)
    
    def _extract_phrases(self, query: str) -> List[str]:
        """Extract important phrases (2-3 words)"""
        words = query.lower().split()
        phrases = []
        
        # Bigrams
        for i in range(len(words) - 1):
            phrases.append(' '.join(words[i:i+2]))
        
        # Trigrams
        for i in range(len(words) - 2):
            phrases.append(' '.join(words[i:i+3]))
        
        return phrases