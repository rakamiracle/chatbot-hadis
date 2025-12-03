"""
Backfill chat embeddings for existing chat history

This script generates embeddings for chat records that don't have them yet.
It creates three embeddings: query_embedding, response_embedding, and combined_embedding.

Jalankan: python scripts/backfill_chat_embeddings.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, or_
from app.database.connection import get_db
from app.models.chat_history import ChatHistory
from app.services.embedding_service import EmbeddingService

async def backfill_chat_embeddings():
    """Backfill embeddings for existing chat history"""
    
    embed_service = EmbeddingService()
    
    async for db in get_db():
        try:
            print("=" * 70)
            print("BACKFILLING CHAT HISTORY EMBEDDINGS")
            print("=" * 70)
            
            # Find chats without embeddings (any of the three)
            print("\n1. Finding chat records without embeddings...")
            result = await db.execute(
                select(ChatHistory)
                .where(
                    or_(
                        ChatHistory.query_embedding.is_(None),
                        ChatHistory.response_embedding.is_(None),
                        ChatHistory.combined_embedding.is_(None)
                    )
                )
                .order_by(ChatHistory.id)
            )
            chats_without_embeddings = result.scalars().all()
            
            if len(chats_without_embeddings) == 0:
                print("   ✓ All chat records already have embeddings!")
                print("\n" + "=" * 70)
                return
            
            print(f"   Found {len(chats_without_embeddings)} chat records without embeddings")
            
            # Process each chat
            processed = 0
            failed = 0
            
            for i, chat in enumerate(chats_without_embeddings, 1):
                try:
                    print(f"\n{i}/{len(chats_without_embeddings)}. Processing chat ID: {chat.id}")
                    
                    # Truncate texts if needed
                    query_text = chat.user_query[:2000] if len(chat.user_query) > 2000 else chat.user_query
                    answer_text = chat.bot_response[:2000] if len(chat.bot_response) > 2000 else chat.bot_response
                    combined_text = f"Q: {query_text} A: {answer_text}"
                    if len(combined_text) > 2000:
                        combined_text = combined_text[:2000]
                    
                    print(f"   Query: {chat.user_query[:50]}...")
                    print(f"   Generating embeddings...")
                    
                    # Generate embeddings
                    query_embedding = await embed_service.generate_embedding(query_text)
                    response_embedding = await embed_service.generate_embedding(answer_text)
                    combined_embedding = await embed_service.generate_embedding(combined_text)
                    
                    # Update chat record
                    chat.query_embedding = query_embedding
                    chat.response_embedding = response_embedding
                    chat.combined_embedding = combined_embedding
                    
                    await db.commit()
                    
                    print("   ✓ Embeddings generated and saved")
                    processed += 1
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    failed += 1
                    await db.rollback()
                    continue
            
            # Summary
            print("\n" + "=" * 70)
            print("BACKFILL SUMMARY")
            print("=" * 70)
            print(f"✅ Successfully processed: {processed}")
            if failed > 0:
                print(f"❌ Failed: {failed}")
            print(f"📊 Total: {len(chats_without_embeddings)}")
            print("\n" + "=" * 70)
            
        except Exception as e:
            print(f"\n❌ Error during backfill: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(backfill_chat_embeddings())
