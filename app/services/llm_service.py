import asyncio
import ollama
from typing import List, Dict, Optional
from config import settings
from app.utils.logger import logger

class LLMService:
    def __init__(self):
        self.model = settings.OLLAMA_MODEL
        self.fallback_responses = {
            "no_context": "Maaf, saya tidak menemukan informasi yang relevan dalam dokumen hadis yang tersedia untuk menjawab pertanyaan Anda. Silakan coba pertanyaan lain atau upload dokumen hadis yang lebih sesuai.",
            "error": "Maaf, terjadi kesalahan teknis saat memproses pertanyaan Anda. Tim kami telah dicatat error ini. Silakan coba lagi dalam beberapa saat.",
            "timeout": "Maaf, pemrosesan memakan waktu terlalu lama. Silakan coba dengan pertanyaan yang lebih spesifik atau coba lagi nanti."
        }
    
    async def generate_response(self, query: str, context_chunks: List[Dict]) -> str:
        """Generate response dengan fallback mechanism"""
        
        # Check if we have context
        if not context_chunks:
            logger.warning(f"No context chunks for query: {query}")
            return self.fallback_responses["no_context"]
        
        # Build context
        context_parts = []
        for i, chunk in enumerate(context_chunks[:3], 1):
            meta = chunk.get('metadata', {})
            
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
        
        # Enhanced prompt
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
            # Try to generate response with timeout
            logger.info(f"Generating LLM response for query: {query[:100]}...")
            
            response = await asyncio.wait_for(
                self._generate_with_ollama(prompt),
                timeout=30.0  # 30 second timeout
            )
            
            # Validate response
            if not response or len(response.strip()) < 10:
                logger.warning("LLM returned empty/short response")
                return self._generate_fallback_response(query, context_chunks)
            
            logger.info("LLM response generated successfully")
            return response.strip()
        
        except asyncio.TimeoutError:
            logger.error(f"LLM timeout for query: {query}")
            return self.fallback_responses["timeout"]
        
        except Exception as e:
            logger.error(f"LLM error: {str(e)}")
            return self._generate_fallback_response(query, context_chunks, error=str(e))
    
    async def _generate_with_ollama(self, prompt: str) -> str:
        """Generate response using Ollama"""
        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            options={
                "temperature": 0.3,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 600,
                "stop": ["\n\nPERTANYAAN:", "KONTEKS:"]
            }
        )
        return response['response']
    
    def _generate_fallback_response(self, query: str, chunks: List[Dict], error: Optional[str] = None) -> str:
        """Generate fallback response dari context chunks"""
        logger.warning(f"Using fallback response mechanism. Error: {error}")
        
        # Build simple response dari chunks
        response = "Berdasarkan dokumen hadis yang tersedia:\n\n"
        
        for i, chunk in enumerate(chunks[:2], 1):
            meta = chunk.get('metadata', {})
            response += f"{i}. "
            
            if meta.get('kitab'):
                response += f"Dari {meta['kitab']} "
            if meta.get('perawi'):
                response += f"(HR. {meta['perawi']}) "
            
            response += f"pada halaman {chunk['page_number']}:\n"
            response += f"{chunk['text'][:300]}...\n\n"
        
        response += "Untuk informasi lebih detail, silakan merujuk langsung ke sumber dokumen."
        
        return response