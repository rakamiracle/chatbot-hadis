import ollama
from typing import List, Dict
from config import settings

class LLMService:
    def __init__(self):
        self.model = settings.OLLAMA_MODEL
    
    async def generate_response(self, query: str, context_chunks: List[Dict]) -> str:
        # Build context
        context = "\n\n".join([
            f"[Hadis {i+1}] {chunk['text'][:500]}..."
            for i, chunk in enumerate(context_chunks)
        ])
        
        # Build prompt
        prompt = f"""Kamu adalah asisten ahli hadis. Jawab pertanyaan berikut berdasarkan HANYA pada konteks hadis yang diberikan.

Konteks Hadis:
{context}

Pertanyaan: {query}

Jawaban (sertakan referensi nomor hadis jika relevan):"""
        
        # Call Ollama
        response = ollama.generate(
            model=self.model,
            prompt=prompt
        )
        
        return response['response']