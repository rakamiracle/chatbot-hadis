from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
from config import settings

class EmbeddingService:
    def __init__(self):
        print(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    async def generate_embedding(self, text: str) -> List[float]:
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts)
        return [emb.tolist() for emb in embeddings]