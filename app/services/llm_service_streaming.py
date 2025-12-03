import ollama
from typing import List, Dict, Optional, AsyncGenerator
from config import settings
from app.utils.logger import logger
import asyncio
import re

class LLMServiceStreaming:
    """LLM Service dengan streaming untuk response yang lebih cepat terasa"""
    
    def __init__(self):
        self.model = settings.OLLAMA_MODEL
        self.fallback_responses = {
            "no_context": "Maaf, saya tidak menemukan informasi yang relevan dalam dokumen hadis yang tersedia untuk menjawab pertanyaan Anda. Silakan coba pertanyaan lain atau upload dokumen hadis yang lebih sesuai.",
            "error": "Maaf, terjadi kesalahan teknis saat memproses pertanyaan Anda. Silakan coba lagi.",
            "timeout": "Maaf, pemrosesan memakan waktu terlalu lama. Silakan coba dengan pertanyaan yang lebih spesifik."
        }
    
    async def generate_response_stream(
        self, 
        query: str, 
        context_chunks: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """Generate response dengan streaming untuk perceived speed"""
        
        if not context_chunks:
            logger.warning(f"No context chunks for query: {query}")
            yield self.fallback_responses["no_context"]
            return
        
        # Detect query type
        query_type = self._detect_query_type(query)
        
        # Build optimized context
        context = self._build_optimized_context(context_chunks, query_type)
        
        # Build optimized prompt
        prompt = self._build_prompt(query, context, query_type)
        
        try:
            logger.info(f"Generating streaming LLM response (type: {query_type})...")
            
            # Stream response
            async for chunk in self._stream_with_ollama(prompt):
                yield chunk
            
            logger.info("Streaming response completed")
        
        except asyncio.TimeoutError:
            logger.error(f"LLM timeout for query: {query}")
            yield self.fallback_responses["timeout"]
        
        except Exception as e:
            logger.error(f"LLM error: {str(e)}")
            yield self._generate_fallback_response(query, context_chunks, error=str(e))
    
    async def _stream_with_ollama(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from Ollama"""
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        def _generate():
            return ollama.generate(
                model=self.model,
                prompt=prompt,
                stream=True,  # Enable streaming
                options={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 20,
                    "num_predict": 200,
                    "stop": ["\n\n", "PERTANYAAN:", "KONTEKS:"],
                    "num_ctx": 1024,
                    "num_thread": 4,
                }
            )
        
        # Get streaming generator
        stream = await loop.run_in_executor(None, _generate)
        
        # Yield chunks
        for chunk in stream:
            if 'response' in chunk:
                yield chunk['response']
    
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
