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
            "no_context": "Maaf, saya tidak menemukan hadis yang relevan dengan pertanyaan Anda. Silakan coba dengan pertanyaan yang lebih spesifik.",
            "error": "Maaf, terjadi kesalahan teknis saat memproses pertanyaan Anda. Silakan coba lagi.",
            "timeout": "Maaf, pemrosesan memakan waktu terlalu lama. Silakan coba dengan pertanyaan yang lebih spesifik."
        }
    
    async def generate_response(self, query: str, context_chunks: List[Dict], force_arabic: Optional[bool] = None) -> tuple:
        """
        Generate response dengan optimized prompting
        
        🔥 IMPROVEMENTS:
        1. Better metadata extraction from chunks
        2. Improved source citation format
        3. Better quality control
        
        Args:
            force_arabic: None=auto detect, True=force show, False=force hide
            
        Returns:
            tuple: (answer: str, include_arabic: bool)
        """
        
        if not context_chunks:
            logger.warning(f"⚠️  No context chunks for query: {query}")
            return self.fallback_responses["no_context"], False
        
        # Detect query type
        query_type = self._detect_query_type(query)
        
        # Determine if need Arabic
        if force_arabic is True:
            include_arabic = True
        elif force_arabic is False:
            include_arabic = False
        else:
            include_arabic = self._detect_need_arabic(query, query_type)
        
        # 🔥 IMPROVED: Extract and format metadata properly
        context = self._build_context_with_metadata(context_chunks, query_type)
        
        # Build prompt with better structure
        prompt = self._build_improved_prompt(query, context, query_type, include_arabic)
        
        try:
            logger.info(f"🤖 Generating LLM response (type: {query_type}, arabic: {include_arabic})...")
            
            response = await asyncio.wait_for(
                self._generate_with_ollama(prompt),
                timeout=30.0
            )
            
            if not response or len(response.strip()) < 10:
                logger.warning("⚠️  LLM returned empty/short response")
                return self._generate_fallback_response(query, context_chunks), include_arabic
            
            # Post-process response
            response = self._post_process_response(response, context_chunks)
            
            logger.info("✅ LLM response generated successfully")
            return response.strip(), include_arabic
        
        except asyncio.TimeoutError:
            logger.error(f"❌ LLM timeout (30s) for query: {query}")
            return self._timeout_response(context_chunks), include_arabic
        
        except Exception as e:
            logger.error(f"❌ LLM error: {str(e)}", exc_info=True)
            return self._error_response(context_chunks), include_arabic
    
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
    
    def _build_context_with_metadata(self, chunks: List[Dict], query_type: str) -> str:
        """
        🔥 IMPROVED: Build context dengan proper metadata extraction
        
        Extract dan display metadata dengan format yang jelas
        """
        
        top_chunks = sorted(chunks, key=lambda x: x.get('final_score', x['similarity']), reverse=True)[:2]
        
        context_parts = []
        
        for i, chunk in enumerate(top_chunks, 1):
            meta = chunk.get('metadata', {})
            
            # Build metadata header
            header_parts = []
            
            # 📚 Kitab
            kitab = meta.get('kitab') or chunk.get('kitab_name')
            if kitab:
                header_parts.append(f"Kitab: {kitab}")
            
            # 📖 Bab
            if meta.get('bab'):
                bab_info = f"Bab"
                if meta.get('bab_nomor'):
                    bab_info += f" {meta['bab_nomor']}"
                bab_info += f": {meta['bab']}"
                header_parts.append(bab_info)
            
            # 🔢 Nomor Hadis
            if meta.get('nomor_hadis') or meta.get('hadis_number'):
                hadis_num = meta.get('nomor_hadis') or meta.get('hadis_number')
                header_parts.append(f"Hadis No. {hadis_num}")
            
            # 👤 Perawi
            if meta.get('perawi'):
                header_parts.append(f"HR. {meta['perawi']}")
            
            # ✨ Derajat
            if meta.get('derajat'):
                header_parts.append(f"({meta['derajat']})")
            
            # Format header
            if header_parts:
                context_parts.append(f"[Sumber {i}] {' | '.join(header_parts)}")
            else:
                context_parts.append(f"[Sumber {i}]")
            
            # Text content
            text = chunk['text']
            if len(text) > 400:
                text = text[:400] + "..."
            
            context_parts.append(text)
            
            # Add metadata sebagai notes
            notes = []
            if meta.get('arab'):
                notes.append(f"(Arab: {meta['arab'][:100]}...)")
            
            if notes:
                context_parts.append(" ".join(notes))
            
            context_parts.append("---")
        
        return "\n\n".join(context_parts)
    
    def _detect_need_arabic(self, query: str, query_type: str) -> bool:
        """Detect apakah perlu tampilkan teks Arab"""
        query_lower = query.lower()
        
        # Explicit keywords - ALWAYS show Arabic
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
        
        # Hafalan context - ALWAYS show Arabic
        hafalan_keywords = [
            'doa', 'dzikir', 'zikir', 'wirid', 'shalawat',
            'bacaan', 'dibaca', 'membaca', 'baca',
            'hafal', 'menghafal', 'menghafalkan',
            'tasbih', 'tahmid', 'tahlil', 'takbir'
        ]
        
        for keyword in hafalan_keywords:
            if keyword in query_lower:
                return True
        
        # Specific reference - Show Arabic
        if any(word in query_lower for word in ['nomor', 'no.', 'hadis ke', 'hadits ke', 'hadis no', '#']):
            return True
        
        # Default: HIDE Arabic untuk pertanyaan umum
        return False
    
    def _build_improved_prompt(self, query: str, context: str, query_type: str, include_arabic: bool) -> str:
        """Build improved prompt dengan instruksi lebih jelas"""
        
        type_instructions = {
            'definition': "Berikan definisi yang jelas dan ringkas (2-3 kalimat).",
            'howto': "Jelaskan langkah-langkah secara berurutan dan mudah dipahami.",
            'reason': "Jelaskan alasan, hikmah, atau tujuan dibalik hukum tersebut.",
            'perawi': "Fokus pada informasi tentang perawi dan riwayatannya.",
            'number': "Sebutkan referensi nomor atau angka yang spesifik.",
            'general': "Berikan jawaban yang informatif dan sesuai dengan konteks hadis.",
        }
        
        base_instruction = f"Anda adalah asisten ahli hadis Islam yang terpercaya. {type_instructions.get(query_type, type_instructions['general'])}"
        
        format_instruction = """
🔴 WAJIB DIPATUHI:
1. Jawab HANYA berdasarkan konteks hadis yang diberikan
2. Jika konteks tidak relevan, katakan jujur: "Maaf, tidak ada hadis yang sesuai..."
3. SELALU cantumkan sumber dengan format: (Kitab [Nama], Hadis No. [Nomor], HR. [Perawi])
4. Jangan mengarang nomor hadis atau perawi yang tidak ada
5. Hindari pernyataan yang berlebihan atau spekulatif
6. Jawab singkat dan fokus (2-4 kalimat)
"""
        
        format_examples = """
CONTOH JAWABAN YANG BENAR:
✅ "Wudhu adalah bersuci menggunakan air untuk menghilangkan hadats (Shahih Bukhari, Hadis No. 159, HR. Bukhari). Wudhu wajib dilakukan sebelum shalat dan mencakup mencuci anggota tubuh tertentu dengan tertib."

✅ "Maaf, konteks hadis yang disediakan tidak sesuai untuk menjawab pertanyaan tentang [topik Anda]. Silakan coba dengan kata kunci yang lebih spesifik."
"""
        
        prompt = f"""{base_instruction}

{format_instruction}

{format_examples}

KONTEKS HADIS:
{context}

PERTANYAAN: {query}

JAWABAN ANDA:"""
        
        return prompt
    
    async def _generate_with_ollama(self, prompt: str) -> str:
        """Generate response using Ollama with optimized settings"""
        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            options={
                "temperature": 0.1,          # Low temperature untuk consistency
                "top_p": 0.8,
                "top_k": 20,
                "num_predict": 300,          # Limit output length
                "stop": ["PERTANYAAN:", "KONTEKS:", "---"],
                "num_ctx": 1024,
                "num_thread": 4,
            }
        )
        return response['response']
    
    def _post_process_response(self, response: str, chunks: List[Dict]) -> str:
        """Post-process LLM response untuk quality improvement"""
        
        # Remove duplicate lines
        lines = response.split('\n')
        unique_lines = []
        seen = set()
        
        for line in lines:
            line_clean = line.strip().lower()
            if line_clean and line_clean not in seen:
                unique_lines.append(line.strip())
                seen.add(line_clean)
        
        response = '\n'.join(unique_lines)
        
        # Ensure tidak terlalu panjang
        if len(response) > 800:
            sentences = re.split(r'[.!?]', response)
            response = '. '.join(sentences[:6]) + '.'
        
        return response
    
    def _generate_fallback_response(self, query: str, chunks: List[Dict]) -> str:
        """Generate fallback response dari context chunks"""
        logger.warning(f"📝 Using fallback response for query: {query[:50]}...")
        
        if not chunks:
            return self.fallback_responses["no_context"]
        
        top_chunk = chunks[0]
        meta = top_chunk.get('metadata', {})
        
        response = ""
        
        # Add source info
        if meta.get('kitab'):
            response += f"Berdasarkan {meta['kitab']} "
        if meta.get('perawi'):
            response += f"(HR. {meta['perawi']}) "
        
        response += f"halaman {top_chunk.get('page_number')}:\n\n"
        response += top_chunk['text'][:500]
        
        return response
    
    def _timeout_response(self, chunks: List[Dict]) -> str:
        """Response when LLM times out"""
        response = (
            "⏱️ Pemrosesan memakan waktu lebih lama dari biasa.\n\n"
            "💡 **Silakan coba:**\n"
            "- Pertanyaan yang lebih spesifik\n"
            "- Gunakan kata kunci yang lebih detail\n\n"
            "Sementara itu, berikut sumber yang relevan:\n\n"
        )
        response += self._generate_fallback_response("", chunks)
        return response
    
    def _error_response(self, chunks: List[Dict]) -> str:
        """Response when LLM error"""
        response = (
            "❌ Terjadi kesalahan teknis saat memproses pertanyaan.\n\n"
            "💡 **Saran:**\n"
            "- Coba lagi dengan pertanyaan yang lebih sederhana\n"
            "- Atau lihat sumber hadis di bawah untuk referensi manual\n\n"
            "Sumber yang relevan:\n\n"
        )
        response += self._generate_fallback_response("", chunks)
        return response

# Global instance
llm_service = LLMService()