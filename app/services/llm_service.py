import ollama
from typing import List, Dict, Optional
from config import settings
from app.utils.logger import logger
import asyncio
import re

class LLMService:
    def __init__(self):
        self.model = settings.OLLAMA_MODEL
        self.fallback_responses = {
            "no_context": "Maaf, saya tidak menemukan informasi yang relevan dalam dokumen hadis yang tersedia untuk menjawab pertanyaan Anda. Silakan coba pertanyaan lain atau upload dokumen hadis yang lebih sesuai.",
            "error": "Maaf, terjadi kesalahan teknis saat memproses pertanyaan Anda. Silakan coba lagi.",
            "timeout": "Maaf, pemrosesan memakan waktu terlalu lama. Silakan coba dengan pertanyaan yang lebih spesifik."
        }
    
    async def generate_response(self, query: str, context_chunks: List[Dict]) -> str:
        """Generate response dengan optimized prompting"""
        
        if not context_chunks:
            logger.warning(f"No context chunks for query: {query}")
            return self.fallback_responses["no_context"]
        
        # Detect query type untuk custom prompt
        query_type = self._detect_query_type(query)
        
        # Build optimized context
        context = self._build_optimized_context(context_chunks, query_type)
        
        # Build optimized prompt
        prompt = self._build_prompt(query, context, query_type)
        
        try:
            logger.info(f"Generating LLM response (type: {query_type})...")
            
            response = await asyncio.wait_for(
                self._generate_with_ollama(prompt),
                timeout=25.0  # Shorter timeout
            )
            
            if not response or len(response.strip()) < 10:
                logger.warning("LLM returned empty/short response")
                return self._generate_fallback_response(query, context_chunks)
            
            # Post-process response
            response = self._post_process_response(response, context_chunks)
            
            logger.info("LLM response generated successfully")
            return response.strip()
        
        except asyncio.TimeoutError:
            logger.error(f"LLM timeout for query: {query}")
            return self.fallback_responses["timeout"]
        
        except Exception as e:
            logger.error(f"LLM error: {str(e)}")
            return self._generate_fallback_response(query, context_chunks, error=str(e))
    
    def _detect_query_type(self, query: str) -> str:
        """Detect type of query untuk optimized prompting"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['siapa', 'perawi', 'rawi']):
            return 'perawi'
        elif any(word in query_lower for word in ['apa', 'definisi', 'pengertian', 'maksud', 'arti']):
            return 'definition'
        elif any(word in query_lower for word in ['bagaimana', 'cara', 'tata cara']):
            return 'howto'
        elif any(word in query_lower for word in ['kenapa', 'mengapa', 'alasan']):
            return 'reason'
        elif any(word in query_lower for word in ['berapa', 'nomor', 'jumlah']):
            return 'number'
        else:
            return 'general'
    
    def _build_optimized_context(self, chunks: List[Dict], query_type: str) -> str:
        """Build context yang lebih concise"""
        
        # Ambil top 3 chunks paling relevan
        top_chunks = sorted(chunks, key=lambda x: x.get('final_score', x['similarity']), reverse=True)[:3]
        
        context_parts = []
        for i, chunk in enumerate(top_chunks, 1):
            meta = chunk.get('metadata', {})
            
            # Concise header
            header = f"[Sumber {i}"
            if meta.get('kitab'):
                header += f" - {meta['kitab']}"
            if meta.get('nomor_hadis'):
                header += f" #{meta['nomor_hadis']}"
            header += "]"
            
            # Relevant text only (trim jika terlalu panjang)
            text = chunk['text']
            if len(text) > 600:
                text = text[:600] + "..."
            
            context_parts.append(f"{header}\n{text}")
        
        return "\n\n".join(context_parts)
    
    def _build_prompt(self, query: str, context: str, query_type: str) -> str:
        """Build optimized prompt based on query type"""
        
        # Base instruction
        base_instruction = "Anda adalah asisten ahli hadis Islam. Jawab berdasarkan konteks hadis yang diberikan."
        
        # Type-specific instruction
        type_instructions = {
            'perawi': "Fokus pada informasi perawi hadis.",
            'definition': "Berikan definisi yang jelas dan ringkas.",
            'howto': "Jelaskan langkah-langkahnya secara berurutan.",
            'reason': "Jelaskan alasan atau hikmahnya.",
            'number': "Sebutkan nomor atau angka yang spesifik.",
            'general': "Berikan jawaban yang komprehensif."
        }
        
        instruction = type_instructions.get(query_type, type_instructions['general'])
        
        prompt = f"""{base_instruction} {instruction}

KONTEKS HADIS:
{context}

PERTANYAAN: {query}

INSTRUKSI:
- Jawab dalam 2-4 kalimat yang padat dan informatif
- Sebut perawi/kitab/nomor jika relevan
- Jika konteks tidak cukup, katakan dengan jujur
- Hindari pengulangan informasi

JAWABAN:"""
        
        return prompt
    
    async def _generate_with_ollama(self, prompt: str) -> str:
        """Generate response using Ollama with optimized settings"""
        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            options={
                "temperature": 0.2,  # Lower untuk konsistensi
                "top_p": 0.85,
                "top_k": 30,
                "num_predict": 400,  # Shorter max length
                "stop": ["\n\nPERTANYAAN:", "KONTEKS:", "INSTRUKSI:"],
                "num_ctx": 2048,  # Context window
            }
        )
        return response['response']
    
    def _post_process_response(self, response: str, chunks: List[Dict]) -> str:
        """Post-process LLM response"""
        
        # Remove potential repetition
        lines = response.split('\n')
        unique_lines = []
        seen = set()
        
        for line in lines:
            line_clean = line.strip().lower()
            if line_clean and line_clean not in seen:
                unique_lines.append(line.strip())
                seen.add(line_clean)
        
        response = ' '.join(unique_lines)
        
        # Ensure tidak terlalu panjang
        if len(response) > 800:
            sentences = re.split(r'[.!?]', response)
            response = '. '.join(sentences[:4]) + '.'
        
        return response
    
    def _generate_fallback_response(self, query: str, chunks: List[Dict], error: Optional[str] = None) -> str:
        """Generate fallback response dari context chunks"""
        logger.warning(f"Using fallback response. Error: {error}")
        
        top_chunk = chunks[0] if chunks else None
        if not top_chunk:
            return self.fallback_responses["no_context"]
        
        meta = top_chunk.get('metadata', {})
        response = ""
        
        if meta.get('kitab'):
            response += f"Berdasarkan {meta['kitab']} "
        if meta.get('perawi'):
            response += f"(HR. {meta['perawi']}) "
        
        response += f"halaman {top_chunk['page_number']}:\n\n"
        response += top_chunk['text'][:400] + "..."
        
        return response