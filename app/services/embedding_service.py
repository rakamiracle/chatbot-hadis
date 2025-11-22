from sentence_transformers import SentenceTransformer
from config import settings

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    async def generate_embedding(self, text: str):
        return self.model.encode(text).tolist()