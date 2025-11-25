import ollama
from typing import List, Dict
from config import settings

class LLMService:
    async def generate_response(self, query: str, context_chunks: List[Dict]) -> str:
        """Generate response dengan prompt khusus hadis"""
        
        # Build rich context dengan metadata
        context_parts = []
        for i, chunk in enumerate(context_chunks[:3], 1):
            meta = chunk.get('metadata', {})
            
            # Format context dengan metadata
            context_str = f"\n=== Sumber {i} (Halaman {chunk['page_number']}) ===\n"
            
            if meta.get('kitab'):
                context_str += f"Kitab: {meta['kitab']}\n"
            if meta.get('nomor_hadis'):
                context_str += f"Nomor Hadis: {meta['nomor_hadis']}\n"
            if meta.get('perawi'):
                context_str += f"Perawi: HR. {meta['perawi']}\n"
            if meta.get('derajat'):
                context_str += f"Derajat: {meta['derajat']}\n"
            
            context_str += f"\nTeks:\n{chunk['text'][:500]}\n"
            context_parts.append(context_str)
        
        context = "\n".join(context_parts)
        
        # Enhanced prompt untuk hadis
        prompt = f"""Anda adalah asisten ahli hadis Islam yang membantu menjawab pertanyaan tentang hadis dengan akurat dan terpercaya.

KONTEKS HADIS:
{context}

PERTANYAAN: {query}

INSTRUKSI:
1. Jawab berdasarkan HANYA konteks hadis yang diberikan di atas
2. Jika ada informasi perawi, kitab, atau nomor hadis, sebutkan dalam jawaban
3. Jika konteks tidak cukup untuk menjawab, katakan dengan jujur
4. Gunakan bahasa yang sopan dan mudah dipahami
5. Jika relevan, sebutkan derajat hadis (shahih/hasan/dhaif)

JAWABAN:"""
        
        try:
            response = ollama.generate(
                model=settings.OLLAMA_MODEL,
                prompt=prompt,
                options={
                    "temperature": 0.3,  # Lower untuk akurasi lebih tinggi
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_predict": 600,
                    "stop": ["\n\nPERTANYAAN:", "KONTEKS:"]
                }
            )
            return response['response'].strip()
        except Exception as e:
            return f"Maaf, terjadi kesalahan dalam menghasilkan jawaban: {str(e)}"