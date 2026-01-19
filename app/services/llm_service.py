import ollama
from typing import List, Dict, Optional
from config import settings
from app.utils.logger import logger
from app.services.fatwa_guard import fatwa_guard  # 🔥 IMPORT FATWA GUARD
import asyncio
import re

class LLMService:
    """
    🔥 IMPROVED V4: Dengan FatwaGuard untuk mencegah jawaban halal/haram yang ngawur
    
    Perubahan V4:
    1. Integrate FatwaGuard untuk validasi topik sensitif
    2. Block pertanyaan tentang halal/haram/wajib/sunnah
    3. Replace dengan safe response jika perlu
    4. Add disclaimer otomatis untuk topik hati-hati
    5. Log semua blocked/replaced responses
    """
    
    def __init__(self):
        self.model = settings.OLLAMA_MODEL
        self.fallback_responses = {
            "no_context": "Maaf, saya tidak menemukan hadis yang relevan dengan pertanyaan Anda. Silakan coba dengan pertanyaan yang lebih spesifik.",
            "error": "Maaf, terjadi kesalahan teknis saat memproses pertanyaan Anda. Silakan coba lagi.",
            "timeout": "Maaf, pemrosesan memakan waktu terlalu lama. Silakan coba dengan pertanyaan yang lebih spesifik.",
            "low_confidence": "Berikut adalah sumber hadis yang relevan dengan pertanyaan Anda:"
        }
        logger.info("🔥 LLMService initialized with FatwaGuard protection")
    
    async def generate_response(self, query: str, context_chunks: List[Dict], force_arabic: Optional[bool] = None) -> tuple:
        """
        Generate response dengan FatwaGuard protection
        
        🔥 V4: Check topik sebelum generate answer
        """
        
        if not context_chunks:
            logger.warning(f"⚠️  No context chunks for query: {query}")
            return self.fallback_responses["no_context"], False
        
        # 🔥 STEP 1: Analyze query dengan FatwaGuard
        query_analysis = fatwa_guard.analyze_query(query)
        logger.info(f"📋 Query Analysis: topic='{query_analysis['topic']}', action='{query_analysis['action']}'")
        
        # 🔥 STEP 2: BLOCK jika topik kritis
        if query_analysis['should_block']:
            logger.error(f"🚨 BLOCKING response for critical topic: {query_analysis['topic']}")
            
            return query_analysis['safe_response'], False  # No arabic text untuk safe response
        
        # Continue dengan normal flow
        metadata_completeness = self._check_metadata_completeness(context_chunks)
        logger.debug(f"📊 Metadata completeness: {metadata_completeness:.0%}")
        
        query_type = self._detect_query_type(query)
        
        if force_arabic is True:
            include_arabic = True
        elif force_arabic is False:
            include_arabic = False
        else:
            include_arabic = self._detect_need_arabic(query, query_type)
        
        context = self._build_context_with_metadata(context_chunks, query_type)
        sources_info = self._extract_sources_info(context_chunks)
        
        # 🔥 IMPROVED: Prompt dengan FatwaGuard awareness
        prompt = self._build_fatwa_aware_prompt(query, context, query_type, include_arabic, sources_info, query_analysis)
        
        try:
            logger.info(f"🤖 Generating LLM response (type: {query_type}, topic: {query_analysis['topic']})...")
            
            response = await asyncio.wait_for(
                self._generate_with_ollama(prompt),
                timeout=45.0
            )
            
            if not response or len(response.strip()) < 10:
                logger.warning("⚠️  LLM returned empty/short response")
                return self._generate_source_based_response(query, context_chunks), include_arabic
            
            # 🔥 STEP 3: Validate response dengan FatwaGuard
            validation_result = fatwa_guard.validate_response(query, response)
            
            logger.info(f"🔍 FatwaGuard validation: is_safe={validation_result['is_safe']}, action='{validation_result['action']}'")
            
            # 🔥 STEP 4: Handle blocked/replaced responses
            if validation_result['should_replace']:
                logger.warning(f"🚨 REPLACING response: {validation_result['reason']}")
                
                return validation_result['replacement'], False
            
            # 🔥 STEP 5: Normal validation
            llm_validation = self._validate_answer(response, sources_info, query)
            
            if not llm_validation['is_valid']:
                logger.warning(f"❌ Answer failed validation: {llm_validation['reason']}")
                return self._generate_source_based_response(query, context_chunks), include_arabic
            
            response = self._post_process_response(response, context_chunks)
            
            # 🔥 STEP 6: Add disclaimer if needed
            if validation_result['should_add_disclaimer']:
                logger.info(f"⚠️  Adding disclaimer for topic: {query_analysis['topic']}")
                response = response + "\n\n" + validation_result['disclaimer']
            
            if llm_validation['confidence'] < 0.4:
                logger.warning(f"⚠️  Very low confidence: {llm_validation['confidence']:.2f}")
                response += f"\n\n⚠️ **Catatan**: Untuk informasi lebih akurat, silakan konsultasikan dengan ulama terpercaya."
            
            logger.info(f"✅ LLM response generated (confidence: {llm_validation['confidence']:.2f})")
            return response.strip(), include_arabic
        
        except asyncio.TimeoutError:
            logger.error(f"❌ LLM timeout (45s) for query: {query}")
            return self._timeout_response(context_chunks), include_arabic
        
        except Exception as e:
            logger.error(f"❌ LLM error: {str(e)}", exc_info=True)
            return self._error_response(context_chunks), include_arabic
    
    def _build_fatwa_aware_prompt(self, query: str, context: str, query_type: str, include_arabic: bool, sources_info: Dict, query_analysis: Dict) -> str:
        """
        🔥 V5: Simplified prompt - fokus pada instruksi positif
        """
        
        # Simplified system instruction
        system_instruction = """Kamu adalah asisten yang membantu menjelaskan hadis dari database.

CARA MENJAWAB:
1. Jelaskan isi dan makna hadis yang ditemukan
2. Sebutkan sumber (kitab, perawi, nomor hadis) jika tersedia
3. Gunakan bahasa Indonesia yang jelas dan mudah dipahami
4. Jika ada beberapa hadis, rangkum poin utamanya

CATATAN PENTING:
- Jawaban harus berdasarkan hadis yang diberikan dalam konteks
- Jika diminta tentang hukum spesifik (halal/haram), ingatkan untuk konsultasi ulama
- Berikan jawaban yang informatif dan edukatif"""
        
        type_instructions = {
            'definition': "Jelaskan makna dan pengertian berdasarkan hadis yang ditemukan.",
            'howto': "Jelaskan tata cara atau panduan berdasarkan hadis yang ditemukan.",
            'reason': "Jelaskan alasan atau hikmah berdasarkan hadis yang ditemukan.",
            'perawi': "Jelaskan informasi tentang perawi hadis yang ditemukan.",
            'number': "Sebutkan angka atau jumlah yang disebutkan dalam hadis.",
            'general': "Jelaskan isi hadis yang relevan dengan pertanyaan.",
        }
        
        instruction = type_instructions.get(query_type, type_instructions['general'])
        
        prompt = f"""{system_instruction}

HADIS DARI DATABASE:
{context}

PERTANYAAN: {query}

INSTRUKSI: {instruction}

JAWABAN:"""
        
        return prompt
    
    def _check_metadata_completeness(self, chunks: List[Dict]) -> float:
        """Check metadata completeness"""
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
        """Validate answer"""
        
        answer_lower = answer.lower()
        
        has_citation = any(indicator in answer for indicator in [
            'kitab', 'hadis', 'hr.', 'perawi', 'diriwayatkan', 'riwayat',
            'shahih', 'hasan', 'dhaif', 'sahih', 'daif', 'derajat'
        ])
        
        source_keywords = sources_info.get('keywords', [])
        query_keywords = set(re.findall(r'\w+', query.lower())) - {'apa', 'itu', 'yang', 'bagaimana', 'kenapa', 'jelaskan', 'tentang'}
        
        matched_keywords = len(query_keywords & set(source_keywords)) / max(len(query_keywords), 1) if query_keywords else 0.5
        
        answer_words = len(answer.split())
        is_reasonable_length = 20 < answer_words < 800
        
        hallucination_flags = [
            r'menurut pendapat saya',
            r'saya pikir',
            r'(bukan hadis|tidak ada hadis)',
        ]
        
        has_hallucination_flag = any(
            re.search(flag, answer_lower) 
            for flag in hallucination_flags
        )
        
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
        
        is_valid = (
            len(answer.strip()) > 20 and
            not has_hallucination_flag
        )
        
        return {
            'is_valid': is_valid,
            'confidence': confidence_score,
            'reason': "Valid answer",
            'citation_found': has_citation,
            'keyword_match': matched_keywords
        }
    
    def _extract_sources_info(self, chunks: List[Dict]) -> Dict:
        """Extract sources info"""
        all_keywords = set()
        kitab_names = []
        perawi_names = []
        
        for chunk in chunks[:3]:
            meta = chunk.get('metadata', {})
            text = chunk.get('text') or chunk.get('chunk_text', '')
            text_lower = text.lower()
            
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
    
    def _detect_query_type(self, query: str) -> str:
        """Detect query type"""
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
        """Build context"""
        
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
            
            text = chunk.get('text') or chunk.get('chunk_text', '')
            if not text:
                text = "[Teks tidak tersedia]"
            
            if len(text) > 500:
                text = text[:500] + "..."
            
            context_parts.append(text)
            context_parts.append("---")
        
        return "\n\n".join(context_parts)
    
    def _detect_need_arabic(self, query: str, query_type: str) -> bool:
        """Detect if need Arabic text"""
        query_lower = query.lower()
        
        explicit_arabic = [
            'arab', 'arabnya', 'tulisan arab', 'bahasa arab',
            'lafadz', 'lafal', 'lafadh', 'lafalnya',
            'teks asli', 'aslinya'
        ]
        
        for keyword in explicit_arabic:
            if keyword in query_lower:
                return True
        
        return False
    
    async def _generate_with_ollama(self, prompt: str) -> str:
        """Generate with Ollama"""
        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            options={
                "temperature": 0.05, # 0.15, sebelumnya segini
                "top_p": 0.7,
                "top_k": 20,
                "num_predict": 400,
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
        """Generate source-based fallback"""
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
            
            text = chunk.get('text') or chunk.get('chunk_text', '')
            if not text:
                text = "[Teks tidak tersedia]"
            
            response += f"\n**Teks Hadis:**\n{text[:400]}\n\n"
            response += "---\n\n"
        
        response += "\n💡 **Catatan**: Untuk penjelasan lebih detail dan hukum yang tepat, konsultasikan dengan ulama terpercaya."
        
        return response
    
    def _timeout_response(self, chunks: List[Dict]) -> str:
        """Timeout response"""
        response = (
            "⏱️ Pemrosesan memakan waktu lebih lama dari biasanya.\n\n"
            "Berikut adalah sumber hadis yang relevan:\n\n"
        )
        response += self._generate_source_based_response("", chunks)
        return response
    
    def _error_response(self, chunks: List[Dict]) -> str:
        """Error response"""
        response = (
            "❌ Terjadi kesalahan teknis saat memproses pertanyaan.\n\n"
            "Berikut adalah sumber hadis yang relevan untuk referensi:\n\n"
        )
        response += self._generate_source_based_response("", chunks)
        return response

# Global instance
llm_service = LLMService()