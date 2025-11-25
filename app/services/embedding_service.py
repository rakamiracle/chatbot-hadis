from sentence_transformers import SentenceTransformer
from typing import List
from config import settings
import re

class EmbeddingService:
    def __init__(self):
        print(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        print("✓ Model loaded")
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text untuk embedding yang lebih baik"""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove harakat Arab (tashkil) untuk consistency
        arabic_diacritics = re.compile(r'[\u064B-\u065F\u0670]')
        text = arabic_diacritics.sub('', text)
        
        # Normalize Arabic letters
        text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
        text = text.replace('ة', 'ه')
        
        return text.strip()
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding dengan preprocessing"""
        processed_text = self._preprocess_text(text)
        embedding = self.model.encode(processed_text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding generation"""
        processed_texts = [self._preprocess_text(t) for t in texts]
        embeddings = self.model.encode(processed_texts, convert_to_numpy=True, normalize_embeddings=True)
        return [emb.tolist() for emb in embeddings]