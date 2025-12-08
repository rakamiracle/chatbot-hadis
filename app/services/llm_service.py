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
    
    async def generate_response(self, query: str, context_chunks: List[Dict], force_arabic: Optional[bool] = None) -> str:
        """Generate response dengan optimized prompting
        
        Args:
            force_arabic: None=auto detect, True=force show, False=force hide
        """
        
        if not context_chunks:
            logger.warning(f"No context chunks for query: {query}")
            return self.fallback_responses["no_context"]
        
        # Detect query type untuk custom prompt
        query_type = self._detect_query_type(query)
        
        # Build optimized context - REDUCED to 2 chunks max
        context = self._build_optimized_context(context_chunks, query_type)
        
        # Build optimized prompt with force_arabic setting
        prompt = self._build_prompt(query, context, query_type, force_arabic)
        
        try:
            logger.info(f"Generating LLM response (type: {query_type})...")
            
            # CRITICAL: Much shorter timeout to prevent 2-minute hangs
            response = await asyncio.wait_for(
                self._generate_with_ollama(prompt),
                timeout=10.0  # REDUCED from 25s to 10s - fail fast!
            )
            
            if not response or len(response.strip()) < 10:
                logger.warning("LLM returned empty/short response")
                return self._generate_fallback_response(query, context_chunks)
            
            # Post-process response
            response = self._post_process_response(response, context_chunks)
            
            logger.info("LLM response generated successfully")
            return response.strip()
        
        except asyncio.TimeoutError:
            logger.error(f"LLM timeout (10s) for query: {query}")
            logger.warning("Using fallback response due to timeout")
            # Return fallback instead of error message
            return self._generate_fallback_response(query, context_chunks)
        
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
        
        # CRITICAL: Reduced to top 2 chunks (from 3) for faster LLM
        top_chunks = sorted(chunks, key=lambda x: x.get('final_score', x['similarity']), reverse=True)[:2]
        
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
            
            # CRITICAL: Reduced max length to 400 (from 600) for faster processing
            text = chunk['text']
            if len(text) > 400:
                text = text[:400] + "..."
            
            context_parts.append(f"{header}\n{text}")
        
        return "\n\n".join(context_parts)
    
    def _detect_need_arabic(self, query: str) -> bool:
        """Deteksi apakah perlu tampilkan teks Arab"""
        query_lower = query.lower()
        
        # Keyword yang trigger tampilan Arab
        arabic_triggers = [
            'arab', 'arabnya', 'tulisan arab',
            'lafadz', 'lafal', 'lafadh', 'lafalnya',
            'bacaan', 'dibaca', 'membaca',
            'teks asli', 'naskah asli',
            'full hadis', 'hadis lengkap', 'lengkap',
            'bunyi', 'bunyinya',
            'doa', 'dzikir', 'zikir',  # Hafalan biasanya perlu Arab
        ]
        
        # Cek apakah ada trigger keyword
        for trigger in arabic_triggers:
            if trigger in query_lower:
                return True
        
        # Deteksi query spesifik (nomor hadis)
        if any(word in query_lower for word in ['nomor', 'no.', 'no ', 'hadis nomor']):
            return True
        
        return False

    def _build_prompt(self, query: str, context: str, query_type: str, force_arabic: Optional[bool] = None) -> str:
        """Build prompt dengan instruksi tampil Arab atau tidak
        
        Args:
            force_arabic: None=auto detect, True=force show, False=force hide
        """
        
        # Tentukan apakah perlu Arab
        if force_arabic is True:
            include_arabic = True
        elif force_arabic is False:
            include_arabic = False
        else:
            # Auto detect dari query
            include_arabic = self._detect_need_arabic(query)
        
        base_instruction = "Anda adalah asisten ahli hadis Islam. Jawab berdasarkan konteks hadis yang diberikan."
        
        # Instruksi berbeda tergantung perlu Arab atau tidak
        if include_arabic:
            format_instruction = """
FORMAT JAWABAN DENGAN ARAB:
1. Tulis teks Arab dari hadis (gunakan ❖ Arab: [teks])
2. Tulis terjemah Indonesia
3. Sebutkan perawi dan referensi
4. Berikan penjelasan singkat jika relevan

Contoh format:
❖ Arab:
[Tulis teks arab dari konteks]

❖ Terjemah:
[Terjemah hadis]

❖ Sumber: HR. Bukhari #123
"""
        else:
            format_instruction = """
INSTRUKSI:
- Jawab dalam 2-4 kalimat yang padat dan informatif
- Sebut perawi/kitab/nomor jika relevan
- JANGAN tampilkan teks Arab kecuali diminta
- Fokus pada penjelasan/jawaban pertanyaan
"""
        
        prompt = f"""{base_instruction}

KONTEKS HADIS:
{context}

PERTANYAAN: {query}

{format_instruction}

JAWABAN:"""
        
        return prompt
    
    async def _generate_with_ollama(self, prompt: str) -> str:
        """Generate response using Ollama with optimized settings"""
        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            options={
                "temperature": 0.1,      # Lower = faster & more deterministic
                "top_p": 0.8,
                "top_k": 20,             # Lower = faster
                "num_predict": 100,      # DRASTICALLY REDUCED from 200 to 100
                "stop": ["\n\n", "PERTANYAAN:", "KONTEKS:"],
                "num_ctx": 512,          # REDUCED from 1024 to 512 for speed
                "num_thread": 4,         # Use CPU threads
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