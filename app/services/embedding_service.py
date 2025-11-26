from sentence_transformers import SentenceTransformer
from typing import List
from config import settings
import re
import numpy as np

class EmbeddingService:
    def __init__(self):
        print(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        print("✓ Model loaded")
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text untuk embedding yang lebih baik"""
        text = re.sub(r'\s+', ' ', text)
        arabic_diacritics = re.compile(r'[\u064B-\u065F\u0670]')
        text = arabic_diacritics.sub('', text)
        text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
        text = text.replace('ة', 'ه')
        return text.strip()
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding dengan preprocessing"""
        processed_text = self._preprocess_text(text)
        embedding = self.model.encode(processed_text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()
    
    async def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Batch embedding generation - OPTIMIZED"""
        processed_texts = [self._preprocess_text(t) for t in texts]
        
        # Encode dengan batch untuk speed
        embeddings = self.model.encode(
            processed_texts, 
            convert_to_numpy=True, 
            normalize_embeddings=True,
            batch_size=batch_size,  # Process multiple at once
            show_progress_bar=False
        )
        
        return [emb.tolist() for emb in embeddings]