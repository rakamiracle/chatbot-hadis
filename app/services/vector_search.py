from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chunk import HadisChunk
from app.models.document import HadisDocument
from typing import List, Dict, Optional
from config import settings
import re
from app.utils.logger import logger

class VectorSearch:
    """
    🔥 IMPROVED V3: Return chunk dengan SEMUA field lengkap
    """
    
    SIMILARITY_THRESHOLDS = {
        'strict': 0.65,
        'normal': 0.40,
        'lenient': 0.20,
        'debug': 0.10
    }
    
    def __init__(self, threshold_mode: str = 'normal'):
        self.threshold = self.SIMILARITY_THRESHOLDS.get(threshold_mode, 0.40)
        self.threshold_mode = threshold_mode
        logger.info(f"🔍 VectorSearch initialized with threshold: {self.threshold} (mode: {threshold_mode})")
    
    async def search_similar(
        self, 
        query_embedding: List[float],
        query_text: str,
        db: AsyncSession, 
        kitab_filter: Optional[str] = None,
        document_ids: Optional[List[int]] = None,
        top_k: int = None
    ) -> List[Dict]:
        """
        🔥 FIXED V3: Return chunk dengan text & metadata lengkap
        """
        
        if top_k is None:
            top_k = settings.TOP_K_RESULTS
        
        logger.debug(f"🔍 Vector search - Query: '{query_text[:50]}...', top_k: {top_k}")
        
        # Extract keywords
        keywords = self._extract_keywords(query_text)
        keyword_set = set(keywords)
        
        # Calculate similarity
        similarity_expr = (1 - HadisChunk.embedding.cosine_distance(query_embedding)).label("similarity")
        
        # Build query
        vector_query = select(
            HadisChunk.id,
            HadisChunk.chunk_text,  # 🔥 IMPORTANT: Include chunk_text
            HadisChunk.page_number,
            HadisChunk.chunk_metadata,
            HadisChunk.document_id,
            HadisDocument.kitab_name,
            similarity_expr
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
        
        # Fetch more for filtering
        fetch_limit = max(top_k * 3, 20)
        
        vector_query = vector_query.order_by(
            HadisChunk.embedding.cosine_distance(query_embedding)
        ).limit(fetch_limit)
        
        result = await db.execute(vector_query)
        rows = result.all()
        
        if not rows:
            logger.warning(f"⚠️  No chunks found for query: '{query_text[:50]}...'")
            return []
        
        # 🔥 FIXED V3: Process results dengan text lengkap
        candidates = []
        
        for row in rows:
            similarity = float(row.similarity)
            
            if similarity < self.threshold:
                logger.debug(f"⏭️  Skipping chunk (similarity {similarity:.4f} < threshold {self.threshold})")
                continue
            
            # Extract metadata
            metadata = row.chunk_metadata or {}
            quality_score = self._calculate_metadata_quality(metadata)
            
            # Keyword matching
            text_words = set(row.chunk_text.lower().split())
            keyword_score = len(keyword_set & text_words) / max(len(keywords), 1)
            
            # 🔥 FIXED V3: Ensure text field ada
            chunk_text = row.chunk_text or ""
            if not chunk_text:
                logger.warning(f"⚠️  Chunk {row.id} has empty text!")
                chunk_text = ""
            
            candidates.append({
                "chunk_id": row.id,
                "text": chunk_text,  # 🔥 IMPORTANT: Always include
                "chunk_text": chunk_text,  # Backup field
                "page_number": row.page_number,
                "similarity": similarity,
                "keyword_score": keyword_score,
                "metadata": metadata,
                "kitab_name": row.kitab_name,
                "document_id": row.document_id,
                "quality_score": quality_score
            })
        
        logger.debug(f"📊 Found {len(candidates)} candidates before ranking")
        
        if not candidates:
            logger.warning(f"⚠️  All chunks below threshold {self.threshold}")
            
            if self.threshold > 0.20:
                logger.info(f"🔄 Fallback: Retrying with lower threshold (0.20)")
                self.threshold = 0.20
                return await self.search_similar(
                    query_embedding, query_text, db, 
                    kitab_filter, document_ids, top_k
                )
            
            return []
        
        # Improved ranking
        ranked = self._improved_rerank(candidates, keywords)
        
        final_results = ranked[:settings.TOP_K_RESULTS]
        
        logger.info(f"✅ Returning {len(final_results)} results (avg similarity: {sum(r['similarity'] for r in final_results) / len(final_results):.4f})")
        
        return final_results
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords dari query"""
        stop_words = {
            'apa', 'adalah', 'yang', 'dalam', 'dari', 'dengan', 'untuk', 'pada', 'di', 'ke', 
            'oleh', 'tentang', 'bagaimana', 'kenapa', 'mengapa', 'siapa', 'kapan', 'dimana',
            'ini', 'itu', 'dan', 'atau', 'jika', 'ketika', 'maka', 'mungkin', 'kalau',
            'sudah', 'akan', 'telah', 'pernah', 'tidak', 'belum', 'ada', 'bukan', 'jelaskan'
        }
        
        words = re.findall(r'\w+', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _calculate_metadata_quality(self, metadata: Dict) -> float:
        """Calculate quality score from metadata"""
        score = 0.5
        
        if metadata.get('hadis_id') or metadata.get('nomor_hadis'):
            score += 0.15
        
        if metadata.get('perawi'):
            score += 0.15
        
        if metadata.get('bab') or metadata.get('bab_nomor'):
            score += 0.10
        
        if metadata.get('kitab'):
            score += 0.10
        
        derajat = metadata.get('derajat', '').lower()
        if derajat in ['shahih', 'sahih', 'hasan']:
            score += 0.20
        elif derajat in ['dhaif', 'daif']:
            score -= 0.10
        
        if metadata.get('arab'):
            score += 0.05
        
        return min(score, 1.0)
    
    def _improved_rerank(self, candidates: List[Dict], keywords: List[str]) -> List[Dict]:
        """Improved ranking algorithm"""
        for c in candidates:
            final_score = (
                (c['similarity'] * 0.50) +
                (c['keyword_score'] * 0.25) +
                (c['quality_score'] * 0.25)
            )
            
            c['final_score'] = min(final_score, 1.0)
        
        ranked = sorted(candidates, key=lambda x: x['final_score'], reverse=True)
        
        return ranked
    
    async def search_with_fallback(
        self,
        query_embedding: List[float],
        query_text: str,
        db: AsyncSession,
        kitab_filter: Optional[str] = None,
        document_ids: Optional[List[int]] = None,
        top_k: int = None
    ) -> List[Dict]:
        """
        Search dengan automatic fallback strategy
        """
        
        results = await self.search_similar(
            query_embedding, query_text, db,
            kitab_filter, document_ids, top_k
        )
        
        # Fallback jika terlalu sedikit hasil
        if len(results) < 3:
            logger.warning(f"⚠️  Only {len(results)} results, trying lenient search...")
            
            lenient_search = VectorSearch(threshold_mode='lenient')
            results = await lenient_search.search_similar(
                query_embedding, query_text, db,
                kitab_filter, document_ids, top_k
            )
        
        # Fallback jika masih sedikit dan ada filters
        if len(results) < 2 and (kitab_filter or document_ids):
            logger.warning(f"⚠️  Still only {len(results)} results, trying without filters...")
            
            results = await self.search_similar(
                query_embedding, query_text, db,
                None, None, top_k
            )
        
        return results