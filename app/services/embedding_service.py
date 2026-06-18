from sentence_transformers import SentenceTransformer
from typing import List
from config import settings
import re
import numpy as np
import torch

class EmbeddingService:
    _instance = None  # Singleton pattern
    
    def __new__(cls):
        """Singleton pattern untuk reuse model instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        print(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        
        # OPTIMIZATION 1: Use GPU if available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL, device=device)
        
        # OPTIMIZATION 2: Enable half precision on GPU for 2x speed
        if device == "cuda":
            self.model.half()
            print("✓ Enabled FP16 for faster GPU inference")
        
        # OPTIMIZATION 3: Warmup model
        _ = self.model.encode("warmup", convert_to_numpy=True)
        
        print("✓ Model loaded and warmed up")
        self._initialized = True
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text untuk embedding yang lebih baik"""
        text = re.sub(r'\s+', ' ', text)
        arabic_diacritics = re.compile(r'[\u064B-\u065F\u0670]')
        text = arabic_diacritics.sub('', text)
        text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
        text = text.replace('ة', 'ه')
        return text.strip()
    
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        processed_text = self._preprocess_text(text)
        embedding = self.model.encode(
            processed_text, 
            convert_to_numpy=True, 
            normalize_embeddings=True,
            show_progress_bar=False
        )
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