import ollama
from typing import List, Dict, Optional
from config import settings
from app.utils.logger import logger
import asyncio
import re

class LLMService:
    """
    🔥 IMPROVED V3: Better fallback handling & metadata awareness
    
    Perubahan V3:
    1. Improve fallback response quality
    2. Detect incomplete metadata
    3. Better error handling
    4. Reduce disclaimer spam
    """
    
    def __init__(self):
        self.model = settings.OLLAMA_MODEL
        self.fallback_responses = {
            "no_context": "Maaf, saya tidak menemukan hadis yang relevan dengan pertanyaan Anda. Silakan coba dengan pertanyaan yang lebih spesifik.",
            "error": "Maaf, terjadi kesalahan teknis saat memproses pertanyaan Anda. Silakan coba lagi.",
            "timeout": "Maaf, pemrosesan memakan waktu terlalu lama. Silakan coba dengan pertanyaan yang lebih spesifik.",
            "low_confidence": "Berikut adalah sumber hadis yang relevan dengan pertanyaan Anda:"
        }
    
    async def generate_response(self, query: str, context_chunks: List[Dict], force_arabic: Optional[bool] = None) -> tuple:
        """
        Generate response dengan anti-hallucination checks
        
        🔥 V3: Improve handling untuk metadata incomplete
        """
        
        if not context_chunks:
            logger.warning(f"⚠️  No context chunks for query: {query}")
            return self.fallback_responses["no_context"], False
        
        # Check metadata completeness
        metadata_completeness = self._check_metadata_completeness(context_chunks)
        logger.debug(f"📊 Metadata completeness: {metadata_completeness:.0%}")
        
        # Detect query type
        query_type = self._detect_query_type(query)
        
        # Determine if need Arabic
        if force_arabic is True:
            include_arabic = True
        elif force_arabic is False:
            include_arabic = False
        else:
            include_arabic = self._detect_need_arabic(query, query_type)
        
        # Build context
        context = self._build_context_with_metadata(context_chunks, query_type)
        sources_info = self._extract_sources_info(context_chunks)
        
        # Build prompt
        prompt = self._build_balanced_prompt(query, context, query_type, include_arabic, sources_info)
        
        try:
            logger.info(f"🤖 Generating LLM response (type: {query_type}, arabic: {include_arabic})...")
            
            response = await asyncio.wait_for(
                self._generate_with_ollama(prompt),
                timeout=45.0
            )
            
            if not response or len(response.strip()) < 10:
                logger.warning("⚠️  LLM returned empty/short response")
                return self._generate_source_based_response(query, context_chunks), include_arabic
            
            # Validate answer
            validation_result = self._validate_answer(response, sources_info, query)
            
            if not validation_result['is_valid']:
                logger.warning(f"❌ Answer failed validation: {validation_result['reason']}")
                return self._generate_source_based_response(query, context_chunks), include_arabic
            
            # Post-process response
            response = self._post_process_response(response, context_chunks)
            
            # Append confidence note hanya jika sangat rendah
            if validation_result['confidence'] < 0.4:
                logger.warning(f"⚠️  Very low confidence: {validation_result['confidence']:.2f}")
                response += f"\n\n⚠️ **Catatan**: Untuk informasi lebih akurat, silakan konsultasikan dengan ulama terpercaya."
            
            logger.info(f"✅ LLM response generated (confidence: {validation_result['confidence']:.2f})")
            return response.strip(), include_arabic
        
        except asyncio.TimeoutError:
            logger.error(f"❌ LLM timeout (45s) for query: {query}")
            return self._timeout_response(context_chunks), include_arabic
        
        except Exception as e:
            logger.error(f"❌ LLM error: {str(e)}", exc_info=True)
            return self._error_response(context_chunks), include_arabic
    
    def _check_metadata_completeness(self, chunks: List[Dict]) -> float:
        """
        🔥 NEW V3: Check how complete the metadata is
        """
        if not chunks:
            return 0.0
        
        total_score = 0.0
        for chunk in chunks[:3]:
            meta = chunk.get('metadata', {})
            
            score = 0.0
            if meta.get('kitab'):
                score += 0.2
            if meta.get('hadis_id') or meta.get('nomor_hadis'):
                score += 0.2
            if meta.get('perawi'):
                score += 0.2
            if meta.get('bab'):
                score += 0.2
            if meta.get('derajat'):
                score += 0.2
            
            total_score += score
        
        return min(total_score / 3.0, 1.0)
    
    def _validate_answer(self, answer: str, sources_info: Dict, query: str) -> Dict:
        """
        Validate answer dengan less strict criteria
        """
        
        answer_lower = answer.lower()
        
        # Check 1: Ada citation?
        has_citation = any(indicator in answer for indicator in [
            'kitab', 'hadis', 'hr.', 'perawi', 'diriwayatkan', 'riwayat',
            'shahih', 'hasan', 'dhaif', 'sahih', 'daif', 'derajat'
        ])
        
        # Check 2: Keywords match?
        source_keywords = sources_info.get('keywords', [])
        query_keywords = set(re.findall(r'\w+', query.lower())) - {'apa', 'itu', 'yang', 'bagaimana', 'kenapa', 'jelaskan', 'tentang'}
        
        matched_keywords = len(query_keywords & set(source_keywords)) / max(len(query_keywords), 1) if query_keywords else 0.5
        
        # Check 3: Length check
        answer_words = len(answer.split())
        is_reasonable_length = 20 < answer_words < 800
        
        # Check 4: Hallucination red flags
        hallucination_flags = [
            r'menurut pendapat saya',
            r'saya pikir',
            r'(bukan hadis|tidak ada hadis)',
        ]
        
        has_hallucination_flag = any(
            re.search(flag, answer_lower) 
            for flag in hallucination_flags
        )
        
        # Calculate confidence
        confidence_score = 0.0
        
        if has_citation:
            confidence_score += 0.4
        else:
            confidence_score += 0.2
        
        if matched_keywords > 0.3:
            confidence_score += 0.3
        else:
            confidence_score += 0.1
        
        if is_reasonable_length:
            confidence_score += 0.2
        
        if not has_hallucination_flag:
            confidence_score += 0.1
        
        # Validation logic
        is_valid = (
            len(answer.strip()) > 20 and
            not has_hallucination_flag
        )
        
        is_confident = confidence_score >= 0.5
        
        logger.debug(f"Answer validation: valid={is_valid}, confident={is_confident}, score={confidence_score:.2f}")
        
        return {
            'is_valid': is_valid,
            'is_confident': is_confident,
            'confidence': confidence_score,
            'reason': "Valid answer",
            'citation_found': has_citation,
            'keyword_match': matched_keywords
        }
    
    def _extract_sources_info(self, chunks: List[Dict]) -> Dict:
        """Extract keywords dan info dari sources"""
        all_keywords = set()
        kitab_names = []
        perawi_names = []
        
        for chunk in chunks[:3]:
            meta = chunk.get('metadata', {})
            text = chunk.get('text') or chunk.get('chunk_text', '')
            text_lower = text.lower()
            
            # Extract keywords
            words = re.findall(r'\w{2,}', text_lower)
            all_keywords.update(words)
            
            if meta.get('kitab'):
                kitab_names.append(meta['kitab'])
            if meta.get('perawi'):
                perawi_names.append(meta['perawi'])
        
        return {
            'keywords': list(all_keywords),
            'kitabs': kitab_names,
            'perawis': perawi_names,
            'total_chunks': len(chunks)
        }
    
    def _build_balanced_prompt(self, query: str, context: str, query_type: str, include_arabic: bool, sources_info: Dict) -> str:
        """
        Build prompt dengan balanced grounding
        """
        
        grounding_instruction = """
🔴 INSTRUCTION UNTUK JAWABAN:

1. JAWAB DARI KONTEKS HADIS
   - Gunakan informasi dari konteks hadis yang diberikan
   - Jangan menambah info dari pengetahuan umum yang tidak di-konteks

2. SERTAKAN CITATION JIKA MEMUNGKINKAN
   - Contoh: "...berdasarkan hadis... (Kitab [Nama], HR. [Perawi])"
   - Tidak wajib setiap kalimat, tapi minimal di akhir statement penting

3. JAWAB LENGKAP DAN JELAS
   - Berikan jawaban yang komprehensif
   - Jangan hanya copy-paste text hadis, tapi jelaskan maknanya
   - Berikan konteks dan penjelasan tambahan

4. HONESTY TENTANG BATASAN
   - Jika konteks tidak cukup, katakan dengan jujur
   - Jangan spekulasi atau buat asumsi

5. FORMAT JAWABAN
   - Jelaskan dengan cara yang mudah dipahami
   - Gunakan poin-poin jika diperlukan
   - Sertakan rujukan hadis di akhir
"""

        type_instructions = {
            'definition': "Berikan penjelasan/definisi yang jelas berdasarkan hadis. Jelaskan makna dan konteksnya.",
            'howto': "Jelaskan langkah-langkah berdasarkan hadis. Bisa dalam bentuk poin-poin yang terstruktur.",
            'reason': "Jelaskan alasan, hikmah, atau tujuan berdasarkan hadis. Interpretasikan makna hadis.",
            'perawi': "Fokus pada informasi perawi. Jelaskan latar belakang atau konteks perawi jika ada.",
            'number': "Sebutkan angka atau detail spesifik dari hadis. Kontekskan dalam konteks hadis.",
            'general': "Jawab pertanyaan berdasarkan konteks hadis. Jelaskan dengan detail yang cukup.",
        }
        
        base_instruction = type_instructions.get(query_type, type_instructions['general'])
        
        prompt = f"""{grounding_instruction}

KONTEKS HADIS:
{context}

PERTANYAAN: {query}

INSTRUKSI KHUSUS: {base_instruction}

JAWABAN:"""
        
        return prompt
    
    def _detect_query_type(self, query: str) -> str:
        """Detect type of query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['siapa', 'perawi', 'rawi']):
            return 'perawi'
        elif any(word in query_lower for word in ['apa', 'definisi', 'pengertian', 'maksud', 'arti']):
            return 'definition'
        elif any(word in query_lower for word in ['bagaimana', 'cara', 'tata cara', 'jelaskan tentang hukum']):
            return 'howto'
        elif any(word in query_lower for word in ['kenapa', 'mengapa', 'alasan']):
            return 'reason'
        elif any(word in query_lower for word in ['berapa', 'nomor', 'jumlah']):
            return 'number'
        else:
            return 'general'
    
    def _build_context_with_metadata(self, chunks: List[Dict], query_type: str) -> str:
        """Build context dengan metadata lengkap"""
        
        top_chunks = sorted(chunks, key=lambda x: x.get('final_score', x.get('similarity', 0)), reverse=True)[:3]
        
        context_parts = []
        
        for i, chunk in enumerate(top_chunks, 1):
            meta = chunk.get('metadata', {})
            
            header_parts = [f"[Sumber {i}]"]
            
            kitab = meta.get('kitab') or chunk.get('kitab_name')
            if kitab:
                header_parts.append(f"Kitab: {kitab}")
            
            if meta.get('bab'):
                bab_info = f"Bab"
                if meta.get('bab_nomor'):
                    bab_info += f" {meta['bab_nomor']}"
                bab_info += f": {meta['bab']}"
                header_parts.append(bab_info)
            
            hadis_num = meta.get('nomor_hadis') or meta.get('hadis_id')
            if hadis_num:
                header_parts.append(f"Hadis No. {hadis_num}")
            
            if meta.get('perawi'):
                header_parts.append(f"HR. {meta['perawi']}")
            
            if meta.get('derajat'):
                header_parts.append(f"({meta['derajat']})")
            
            if header_parts:
                context_parts.append(" | ".join(header_parts))
            
            # 🔥 FIXED V3: Use text field dengan fallback
            text = chunk.get('text') or chunk.get('chunk_text', '')
            if not text:
                logger.warning(f"⚠️  Chunk {chunk.get('chunk_id')} has no text!")
                text = "[Teks tidak tersedia]"
            
            if len(text) > 500:
                text = text[:500] + "..."
            
            context_parts.append(text)
            context_parts.append("---")
        
        return "\n\n".join(context_parts)
    
    def _detect_need_arabic(self, query: str, query_type: str) -> bool:
        """Detect apakah perlu tampilkan teks Arab"""
        query_lower = query.lower()
        
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
        
        hafalan_keywords = [
            'doa', 'dzikir', 'zikir', 'wirid', 'shalawat',
            'bacaan', 'dibaca', 'membaca', 'baca',
            'hafal', 'menghafal', 'menghafalkan',
            'tasbih', 'tahmid', 'tahlil', 'takbir'
        ]
        
        for keyword in hafalan_keywords:
            if keyword in query_lower:
                return True
        
        if any(word in query_lower for word in ['nomor', 'no.', 'hadis ke', 'hadits ke', 'hadis no', '#']):
            return True
        
        return False
    
    async def _generate_with_ollama(self, prompt: str) -> str:
        """Generate response using Ollama"""
        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            options={
                "temperature": 0.15,
                "top_p": 0.7,
                "top_k": 20,
                "num_predict": 400,  # 🔥 INCREASED: 300 → 400
                "stop": ["PERTANYAAN:", "KONTEKS:", "---"],
                "num_ctx": 1024,
                "num_thread": 4,
            }
        )
        return response['response']
    
    def _post_process_response(self, response: str, chunks: List[Dict]) -> str:
        """Post-process response"""
        
        lines = response.split('\n')
        unique_lines = []
        seen = set()
        
        for line in lines:
            line_clean = line.strip().lower()
            if line_clean and line_clean not in seen:
                unique_lines.append(line.strip())
                seen.add(line_clean)
        
        response = '\n'.join(unique_lines)
        
        if len(response) > 1500:
            sentences = re.split(r'[.!?]', response)
            response = '. '.join(sentences[:10]) + '.'
        
        return response
    
    def _generate_source_based_response(self, query: str, chunks: List[Dict]) -> str:
        """
        🔥 IMPROVED V3: Better source-based fallback
        """
        logger.info("📚 Using source-based fallback")
        
        response = "Berikut adalah hadis yang relevan dengan pertanyaan Anda:\n\n"
        
        top_chunks = sorted(chunks, key=lambda x: x.get('final_score', x.get('similarity', 0)), reverse=True)[:3]
        
        for i, chunk in enumerate(top_chunks, 1):
            meta = chunk.get('metadata', {})
            
            response += f"**[Hadis {i}]**\n"
            
            if meta.get('kitab'):
                response += f"📚 Kitab: {meta['kitab']}\n"
            if meta.get('perawi'):
                response += f"👤 Perawi: {meta['perawi']}\n"
            
            hadis_num = meta.get('nomor_hadis') or meta.get('hadis_id')
            if hadis_num:
                response += f"🔢 No. {hadis_num}\n"
            
            if meta.get('derajat'):
                response += f"⭐ Derajat: {meta['derajat']}\n"
            if meta.get('bab'):
                response += f"📖 Bab: {meta['bab']}\n"
            
            text = chunk.get('text') or chunk.get('chunk_text', '')
            if not text:
                text = "[Teks tidak tersedia]"
            
            response += f"\n**Teks Hadis:**\n{text[:400]}\n\n"
            response += "---\n\n"
        
        response += "\n💡 **Catatan**: Untuk penjelasan lebih detail tentang hadis, silakan konsultasikan dengan ulama terpercaya."
        
        return response
    
    def _timeout_response(self, chunks: List[Dict]) -> str:
        """Response when timeout"""
        response = (
            "⏱️ Pemrosesan memakan waktu lebih lama dari biasanya.\n\n"
            "Berikut adalah sumber hadis yang relevan:\n\n"
        )
        response += self._generate_source_based_response("", chunks)
        return response
    
    def _error_response(self, chunks: List[Dict]) -> str:
        """Response when error"""
        response = (
            "❌ Terjadi kesalahan teknis saat memproses pertanyaan.\n\n"
            "Berikut adalah sumber hadis yang relevan untuk referensi:\n\n"
        )
        response += self._generate_source_based_response("", chunks)
        return response

# Global instance
llm_service = LLMService() 