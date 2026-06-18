"""
Document-level vector search service

This service provides semantic search at the document level,
allowing users to find relevant kitabs/documents based on query similarity.
"""
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import HadisDocument
from typing import List, Dict, Optional

class DocumentSearch:
    """Service for document-level semantic search"""
    
    async def search_similar_documents(
        self,
        query_embedding: List[float],
        db: AsyncSession,
        kitab_filter: Optional[str] = None,
        pengarang_filter: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Search for similar documents using vector similarity
        
        Args:
            query_embedding: Query embedding vector
            db: Database session
            kitab_filter: Optional filter by kitab name
            pengarang_filter: Optional filter by pengarang
            top_k: Number of results to return
            
        Returns:
            List of documents with similarity scores
        """
        
        # Calculate similarity
        similarity_expr = (1 - HadisDocument.embedding.cosine_distance(query_embedding)).label("similarity")
        
        # Build query
        query = select(
            HadisDocument.id,
            HadisDocument.filename,
            HadisDocument.kitab_name,
            HadisDocument.pengarang,
            HadisDocument.penerbit,
            HadisDocument.tahun_terbit,
            HadisDocument.total_pages,
            HadisDocument.summary_text,
            similarity_expr
        ).where(
            HadisDocument.embedding.isnot(None)  # Only documents with embeddings
        )
        
        # Apply filters
        conditions = []
        
        if kitab_filter:
            conditions.append(HadisDocument.kitab_name.ilike(f"%{kitab_filter}%"))
        
        if pengarang_filter:
            conditions.append(HadisDocument.pengarang.ilike(f"%{pengarang_filter}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Order by similarity and limit
        query = query.order_by(
            HadisDocument.embedding.cosine_distance(query_embedding)
        ).limit(top_k)
        
        # Execute query
        result = await db.execute(query)
        rows = result.all()
        
        # Format results
        documents = []
        for row in rows:
            similarity = float(row.similarity)
            
            # Only return documents with reasonable similarity
            if similarity >= 0.3:
                documents.append({
                    "document_id": row.id,
                    "filename": row.filename,
                    "kitab_name": row.kitab_name,
                    "pengarang": row.pengarang,
                    "penerbit": row.penerbit,
                    "tahun_terbit": row.tahun_terbit,
                    "total_pages": row.total_pages,
                    "summary": row.summary_text[:200] + "..." if row.summary_text and len(row.summary_text) > 200 else row.summary_text,
                    "similarity": similarity
                })
        
        return documents
    
    async def get_document_stats(self, db: AsyncSession) -> Dict:
        """
        Get statistics about documents with embeddings
        
        Returns:
            Dictionary with stats
        """
        
        # Total documents
        total_result = await db.execute(
            select(func.count(HadisDocument.id))
        )
        total_docs = total_result.scalar()
        
        # Documents with embeddings
        embedded_result = await db.execute(
            select(func.count(HadisDocument.id))
            .where(HadisDocument.embedding.isnot(None))
        )
        embedded_docs = embedded_result.scalar()
        
        # Documents without embeddings
        missing_embeddings = total_docs - embedded_docs
        
        return {
            "total_documents": total_docs,
            "documents_with_embeddings": embedded_docs,
            "documents_without_embeddings": missing_embeddings,
            "embedding_coverage": f"{(embedded_docs / total_docs * 100):.1f}%" if total_docs > 0 else "0%"
        }
