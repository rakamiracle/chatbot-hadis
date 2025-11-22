import ollama
from config import settings

class LLMService:
    async def generate_response(self, query: str, context_chunks: list):
        context = "\n\n".join([f"[Hal.{c['page_number']}] {c['text'][:400]}" for c in context_chunks[:3]])
        prompt = f"""Anda ahli hadis. Jawab berdasarkan konteks berikut:

{context}

Pertanyaan: {query}
Jawaban:"""
        
        response = ollama.generate(model=settings.OLLAMA_MODEL, prompt=prompt)
        return response['response']