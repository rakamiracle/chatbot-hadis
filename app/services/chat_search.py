"""
Chat history search service

This service provides semantic search on chat history,
allowing users to find similar past conversations.
"""
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat_history import ChatHistory
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class ChatSearch:
    """Service for searching chat history using vector similarity"""
    
    async def search_similar_conversations(
        self,
        query_embedding: List[float],
        db: AsyncSession,
        search_type: str = "combined",  # "query", "response", or "combined"
        session_id: Optional[str] = None,
        days_back: Optional[int] = None,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Search for similar past conversations
        
        Args:
            query_embedding: Query embedding vector
            db: Database session
            search_type: Which embedding to search ("query", "response", "combined")
            session_id: Optional filter by session
            days_back: Optional filter by recent days
            top_k: Number of results to return
            
        Returns:
            List of similar conversations with similarity scores
        """
        
        # Select appropriate embedding column
        if search_type == "query":
            embedding_col = ChatHistory.query_embedding
        elif search_type == "response":
            embedding_col = ChatHistory.response_embedding
        else:  # combined
            embedding_col = ChatHistory.combined_embedding
        
        # Calculate similarity
        similarity_expr = (1 - embedding_col.cosine_distance(query_embedding)).label("similarity")
        
        # Build query
        query = select(
            ChatHistory.id,
            ChatHistory.session_id,
            ChatHistory.user_query,
            ChatHistory.bot_response,
            ChatHistory.timestamp,
            similarity_expr
        ).where(
            embedding_col.isnot(None)  # Only chats with embeddings
        )
        
        # Apply filters
        conditions = []
        
        if session_id:
            conditions.append(ChatHistory.session_id == session_id)
        
        if days_back:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            conditions.append(ChatHistory.timestamp >= cutoff_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Order by similarity and limit
        query = query.order_by(
            embedding_col.cosine_distance(query_embedding)
        ).limit(top_k)
        
        # Execute query
        result = await db.execute(query)
        rows = result.all()
        
        # Format results
        conversations = []
        for row in rows:
            similarity = float(row.similarity)
            
            # Only return conversations with reasonable similarity
            if similarity >= 0.3:
                conversations.append({
                    "chat_id": row.id,
                    "session_id": str(row.session_id),
                    "user_query": row.user_query,
                    "bot_response": row.bot_response,
                    "timestamp": row.timestamp.isoformat(),
                    "similarity": similarity
                })
        
        return conversations
    
    async def search_by_query(
        self,
        query_embedding: List[float],
        db: AsyncSession,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Search for similar user queries
        
        Useful for finding when users asked similar questions
        """
        return await self.search_similar_conversations(
            query_embedding, db, search_type="query", top_k=top_k
        )
    
    async def search_by_response(
        self,
        query_embedding: List[float],
        db: AsyncSession,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Search for similar bot responses
        
        Useful for finding answers about similar topics
        """
        return await self.search_similar_conversations(
            query_embedding, db, search_type="response", top_k=top_k
        )
    
    async def get_conversation_context(
        self,
        session_id: str,
        db: AsyncSession,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get recent conversation history for a session
        
        Returns chronological conversation history
        """
        result = await db.execute(
            select(ChatHistory)
            .where(ChatHistory.session_id == session_id)
            .order_by(ChatHistory.timestamp.desc())
            .limit(limit)
        )
        
        chats = result.scalars().all()
        
        return [
            {
                "chat_id": chat.id,
                "user_query": chat.user_query,
                "bot_response": chat.bot_response,
                "timestamp": chat.timestamp.isoformat()
            }
            for chat in reversed(chats)  # Reverse to get chronological order
        ]
    
    async def get_chat_stats(self, db: AsyncSession) -> Dict:
        """
        Get statistics about chat history embeddings
        
        Returns:
            Dictionary with stats
        """
        
        # Total chats
        total_result = await db.execute(
            select(func.count(ChatHistory.id))
        )
        total_chats = total_result.scalar()
        
        # Chats with embeddings
        embedded_result = await db.execute(
            select(func.count(ChatHistory.id))
            .where(ChatHistory.combined_embedding.isnot(None))
        )
        embedded_chats = embedded_result.scalar()
        
        # Missing embeddings
        missing_embeddings = total_chats - embedded_chats
        
        # Unique sessions
        sessions_result = await db.execute(
            select(func.count(func.distinct(ChatHistory.session_id)))
        )
        unique_sessions = sessions_result.scalar()
        
        return {
            "total_chats": total_chats,
            "chats_with_embeddings": embedded_chats,
            "chats_without_embeddings": missing_embeddings,
            "embedding_coverage": f"{(embedded_chats / total_chats * 100):.1f}%" if total_chats > 0 else "0%",
            "unique_sessions": unique_sessions
        }
