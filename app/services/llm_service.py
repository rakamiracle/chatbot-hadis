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
    
    async def generate_response(self, query: str, context_chunks: List[Dict], force_arabic: Optional[bool] = None) -> tuple:
        """Generate response dengan optimized prompting
        
        Args:
            force_arabic: None=auto detect, True=force show, False=force hide
            
        Returns:
            tuple: (answer: str, include_arabic: bool)
        """
        
        if not context_chunks:
            logger.warning(f"No context chunks for query: {query}")
            return self.fallback_responses["no_context"], False
        
        # Detect query type untuk custom prompt
        query_type = self._detect_query_type(query)
        
        # Tentukan apakah perlu Arab
        if force_arabic is True:
            include_arabic = True
        elif force_arabic is False:
            include_arabic = False
        else:
            # Auto detect berdasarkan query dan type
            include_arabic = self._detect_need_arabic(query, query_type)
        
        # Build optimized context - REDUCED to 2 chunks max
        context = self._build_optimized_context(context_chunks, query_type)
        
        # Build optimized prompt with include_arabic setting
        prompt = self._build_prompt(query, context, query_type, include_arabic)
        
        try:
            logger.info(f"Generating LLM response (type: {query_type}, arabic: {include_arabic})...")
            
            # 🔥 FIX 1: Timeout dinaikkan 10s → 30s
            response = await asyncio.wait_for(
                self._generate_with_ollama(prompt),
                timeout=30.0  # ← CHANGED from 10.0
            )
            
            if not response or len(response.strip()) < 10:
                logger.warning("LLM returned empty/short response")
                return self._generate_fallback_response(query, context_chunks), include_arabic
            
            # Post-process response
            response = self._post_process_response(response, context_chunks)
            
            logger.info("LLM response generated successfully")
            return response.strip(), include_arabic
        
        # 🔥 FIX 2: Better error messages
        except asyncio.TimeoutError:
            logger.error(f"LLM timeout (30s) for query: {query}")
            fallback_msg = (
                "⏱️ Pemrosesan memakan waktu lebih lama dari biasa.\n\n"
                "💡 **Tips:** Coba pertanyaan lebih spesifik.\n"
                "Contoh: 'hadis tentang shalat dari Bukhari' atau 'doa sebelum tidur'\n\n"
                f"Sementara, berikut sumber yang relevan:\n\n"
                f"{self._generate_fallback_response(query, context_chunks)}"
            )
            return fallback_msg, include_arabic
        
        except Exception as e:
            logger.error(f"LLM error: {str(e)}", exc_info=True)
            error_msg = (
                "❌ Terjadi kesalahan teknis saat memproses pertanyaan Anda.\n\n"
                "💡 **Saran:**\n"
                "- Coba lagi dengan pertanyaan yang lebih sederhana\n"
                "- Atau lihat sumber hadis di bawah untuk referensi manual\n\n"
                f"Sumber yang relevan:\n\n"
                f"{self._generate_fallback_response(query, context_chunks)}"
            )
            return error_msg, include_arabic
    
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
    
    def _detect_need_arabic(self, query: str, query_type: str) -> bool:
        """Deteksi apakah perlu tampilkan teks Arab
        
        🔥 SIMPLIFIED LOGIC - Lebih akurat & mudah dipahami
        """
        query_lower = query.lower()
        
        # 🔥 Priority 1: Explicit keywords - ALWAYS show Arabic
        explicit_arabic = [
            'arab', 'arabnya', 'tulisan arab', 'bahasa arab',
            'lafadz', 'lafal', 'lafadh', 'lafalnya',
            'bunyi', 'bunyinya', 'berbunyi',
            'teks asli', 'aslinya',
            'full', 'lengkap', 'selengkapnya', 'lengkapnya'
        ]
        
        for keyword in explicit_arabic:
            if keyword in query_lower:
                return True
        
        # 🔥 Priority 2: Hafalan context - ALWAYS show Arabic
        # User butuh Arab untuk dibaca/dihafal
        hafalan_keywords = [
            'doa', 'dzikir', 'zikir', 'wirid', 'shalawat',
            'bacaan', 'dibaca', 'membaca', 'baca',
            'hafal', 'menghafal', 'menghafalkan',
            'tasbih', 'tahmid', 'tahlil', 'takbir'
        ]
        
        for keyword in hafalan_keywords:
            if keyword in query_lower:
                return True
        
        # 🔥 Priority 3: Specific reference - Show Arabic
        # User cari hadis spesifik, biasanya butuh text lengkap
        if any(word in query_lower for word in ['nomor', 'no.', 'hadis ke', 'hadits ke', 'hadis no', '#']):
            return True
        
        # 🔥 Default: HIDE Arabic untuk pertanyaan umum
        # Definisi/cara/alasan biasanya cukup pakai Bahasa Indonesia
        return False

    def _build_prompt(self, query: str, context: str, query_type: str, include_arabic: bool) -> str:
        """Build prompt dengan instruksi tampil Arab atau tidak"""
        
        # Type-specific base instruction
        type_instructions = {
            'definition': "Berikan definisi yang jelas dan ringkas.",
            'howto': "Jelaskan langkah-langkah secara berurutan.",
            'reason': "Jelaskan alasan atau hikmahnya.",
            'perawi': "Fokus pada informasi tentang perawi.",
            'number': "Sebutkan referensi yang spesifik.",
            'general': "Berikan jawaban yang informatif."
        }
        
        base_instruction = f"Anda adalah asisten ahli hadis Islam. {type_instructions.get(query_type, type_instructions['general'])}"
        
        # Instruksi berbeda tergantung perlu Arab atau tidak
        if include_arabic:
            format_instruction = """
FORMAT JAWABAN (WAJIB LENGKAP):
1. 📖 Arab: [tulis teks Arab dari konteks]
2. 📝 Terjemah: [terjemahan lengkap dalam Bahasa Indonesia]
3. 📚 Sumber: [sebutkan perawi, kitab, nomor hadis]
4. ✨ Penjelasan: [berikan penjelasan 2-3 kalimat tentang makna/konteks hadis]

SEMUA 4 BAGIAN DI ATAS WAJIB DIISI. Jangan hanya tulis Arab saja.
"""
        else:
            # 🔥 FIX: Tambahkan instruksi CITATION
            format_instruction = """
INSTRUKSI PENTING:
- Jawab dalam 2-4 kalimat yang informatif dalam Bahasa Indonesia
- 🔥 WAJIB: Sertakan sumber dalam jawaban dengan format (HR. Nama, #nomor)
  Contoh: "...bersuci dengan air (HR. Bukhari #135)"
- DILARANG menulis teks Arab atau huruf Arab
- Fokus menjawab pertanyaan dengan penjelasan yang jelas

CONTOH JAWABAN YANG BENAR:
"Wudhu adalah bersuci menggunakan air untuk menghilangkan hadats kecil (HR. Bukhari #159). 
Wudhu wajib dilakukan sebelum shalat dan mencakup mencuci anggota tubuh tertentu dengan tertib."
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
                "num_predict": 300,      # Increased for complete responses with Arabic
                "stop": ["PERTANYAAN:", "KONTEKS:"],  # Removed \n\n to allow multi-paragraph
                "num_ctx": 1024,         # Increased for better context understanding
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