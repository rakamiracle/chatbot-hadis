"""
🔥 FATWA GUARD SERVICE
Mencegah LLM memberikan jawaban hukum Islam yang ngawur/salah

Fitur:
1. Detect topik sensitif (halal/haram, fiqh, aqidah)
2. Check apakah response mengklaim hukum
3. Replace dengan safe response + disclaimer
4. Log untuk audit
"""

import re
from typing import Dict, Tuple
from app.utils.logger import logger

class FatwaGuard:
    """
    Guard system untuk memastikan jawaban tentang agama Islam AMAN
    dan BERTANGGUNG JAWAB
    """
    
    # 🔴 TOPIK YANG MEMERLUKAN FATWA (HANYA BLOCK JIKA BENAR-BENAR MINTA FATWA)
    # 🔥 V2: Dikurangi agresivitasnya - fokus pada pertanyaan fatwa eksplisit saja
    FORBIDDEN_FATWA_TOPICS = {
        'fatwa_explicit': {
            'keywords': [
                'apa hukumnya', 'hukum dari', 'boleh atau tidak', 'halal atau haram',
                'apakah dosa', 'berdosa jika', 'fatwa tentang', 'minta fatwa'
            ],
            'is_critical': True,
            'safe_response': (
                "Pertanyaan Anda meminta penetapan hukum Islam yang memerlukan fatwa dari ulama yang kompeten.\n\n"
                "ℹ️ **Saya bisa membantu dengan:**\n"
                "- Menampilkan hadis yang relevan dengan topik Anda\n"
                "- Menjelaskan isi dan makna hadis\n"
                "- Memberikan konteks sejarah dan perawi\n\n"
                "⚠️ **Untuk keputusan hukum (halal/haram/wajib)**, silakan konsultasi dengan ulama terpercaya.\n\n"
                "Berikut sumber hadis yang relevan:"
            )
        },
        
        'sensitive_family': {
            'keywords': [
                'talak sah', 'cerai sah', 'nikah siri', 'pernikahan sah atau tidak'
            ],
            'is_critical': True,
            'safe_response': (
                "Pertanyaan Anda menyangkut status keluarga yang memerlukan keputusan resmi.\n\n"
                "⚠️ **PENTING**: Untuk masalah talak, nikah, dan status pernikahan:\n"
                "- Konsultasi dengan Pengadilan Agama\n"
                "- Konsultasi dengan ulama/kyai berpengalaman\n\n"
                "Berikut hadis yang terkait untuk referensi:"
            )
        }
    }
    
    # 🟡 TOPIK YANG BOLEH DIJAWAB TAPI DENGAN HATI-HATI
    CAREFUL_TOPICS = {
        'sejarah_hadis': {
            'keywords': ['sejarah', 'siapa yang meriwayatkan', 'perawi', 'sanad', 'isnad'],
            'disclaimer': (
                "⚠️ **Catatan**: Informasi ini tentang sejarah dan perawi hadis, bukan tentang hukum. "
                "Untuk memahami hukum dari hadis, Anda perlu bimbingan ulama."
            )
        },
        'cerita_nabi': {
            'keywords': ['cerita', 'kisah', 'sejarah nabi', 'peristiwa'],
            'disclaimer': (
                "⚠️ **Catatan**: Ini adalah cerita/sejarah dari hadis. "
                "Untuk hikmah dan pelajaran yang tepat, diskusikan dengan ulama."
            )
        },
        'terjemahan_hadis': {
            'keywords': ['arti', 'makna', 'terjemahan'],
            'disclaimer': (
                "⚠️ **Catatan**: Terjemahan hadis bisa berbeda-beda. "
                "Untuk pemahaman yang akurat, konsultasikan dengan tafsir hadis yang terpercaya."
            )
        }
    }
    
    def __init__(self):
        self.checked_count = 0
        self.flagged_count = 0
        logger.info("🔥 FatwaGuard initialized - Anti-hallucination untuk Islam")
    
    def analyze_query(self, query: str) -> Dict:
        """
        Analisa query untuk mendeteksi topik sensitif
        
        Returns:
            {
                'topic': str,
                'is_critical': bool,
                'should_block': bool,
                'recommendation': str,
                'safe_response': str or None
            }
        """
        query_lower = query.lower()
        
        # Check forbidden topics
        for topic, config in self.FORBIDDEN_FATWA_TOPICS.items():
            for keyword in config['keywords']:
                if keyword in query_lower:
                    logger.warning(f"🚨 Detected CRITICAL topic: {topic} | Query: {query[:50]}")
                    
                    return {
                        'topic': topic,
                        'is_critical': config['is_critical'],
                        'should_block': True,
                        'recommendation': f"Topic '{topic}' memerlukan fatwa dari ulama",
                        'safe_response': config['safe_response'],
                        'action': 'BLOCK_AND_REPLACE'
                    }
        
        # Check careful topics
        for topic, config in self.CAREFUL_TOPICS.items():
            for keyword in config['keywords']:
                if keyword in query_lower:
                    logger.info(f"⚠️  Detected CAREFUL topic: {topic}")
                    
                    return {
                        'topic': topic,
                        'is_critical': False,
                        'should_block': False,
                        'recommendation': f"Topic '{topic}' perlu disclaimer",
                        'safe_response': None,
                        'disclaimer': config['disclaimer'],
                        'action': 'ADD_DISCLAIMER'
                    }
        
        # Safe topic
        return {
            'topic': 'general',
            'is_critical': False,
            'should_block': False,
            'recommendation': 'Topic aman untuk dijawab',
            'safe_response': None,
            'action': 'ALLOW'
        }
    
    def validate_response(self, query: str, answer: str) -> Dict:
        """
        Validasi response untuk memastikan tidak mengklaim hukum sembarangan
        
        Returns:
            {
                'is_safe': bool,
                'reason': str,
                'should_replace': bool,
                'replacement': str or None,
                'should_add_disclaimer': bool,
                'disclaimer': str or None
            }
        """
        self.checked_count += 1
        
        # First, analyze query
        query_analysis = self.analyze_query(query)
        
        if query_analysis['should_block']:
            self.flagged_count += 1
            logger.error(f"🚨 BLOCKING response for critical topic: {query_analysis['topic']}")
            
            return {
                'is_safe': False,
                'reason': f"Topik '{query_analysis['topic']}' memerlukan fatwa dari ulama, bukan AI",
                'should_replace': True,
                'replacement': query_analysis['safe_response'],
                'should_add_disclaimer': False,
                'disclaimer': None,
                'action': 'BLOCK_AND_REPLACE'
            }
        
        # Check if answer contains forbidden claims
        forbidden_claims = self._detect_forbidden_claims(answer, query_analysis['topic'])
        
        if forbidden_claims['has_forbidden_claim']:
            self.flagged_count += 1
            logger.warning(f"🚨 Answer contains forbidden claim: {forbidden_claims['claim_type']}")
            
            return {
                'is_safe': False,
                'reason': f"Jawaban mengklaim '{forbidden_claims['claim_type']}' tanpa ulama",
                'should_replace': True,
                'replacement': self._create_safe_alternative(query_analysis['topic']),
                'should_add_disclaimer': False,
                'disclaimer': None,
                'action': 'REPLACE_ANSWER'
            }
        
        # Check if need disclaimer
        if query_analysis['action'] == 'ADD_DISCLAIMER':
            logger.info(f"⚠️  Adding disclaimer to response for topic: {query_analysis['topic']}")
            
            return {
                'is_safe': True,
                'reason': 'Safe topic tapi perlu disclaimer',
                'should_replace': False,
                'replacement': None,
                'should_add_disclaimer': True,
                'disclaimer': query_analysis['disclaimer'],
                'action': 'ADD_DISCLAIMER'
            }
        
        # Safe response
        return {
            'is_safe': True,
            'reason': 'Response aman',
            'should_replace': False,
            'replacement': None,
            'should_add_disclaimer': False,
            'disclaimer': None,
            'action': 'ALLOW'
        }
    
    def _detect_forbidden_claims(self, answer: str, topic: str) -> Dict:
        """
        Deteksi apakah jawaban mengklaim sesuatu yang berbahaya
        """
        answer_lower = answer.lower()
        
        # Forbidden patterns yang menunjukkan klaim hukum
        forbidden_patterns = [
            r'(jadi\s+)?hukumnya\s+(adalah|yaitu)',  # "jadi hukumnya adalah..."
            r'(jadi\s+)?wajib\s+',                      # "jadi wajib..."
            r'(jadi\s+)?haram\s+',                      # "jadi haram..."
            r'(jadi\s+)?halal\s+',                      # "jadi halal..."
            r'(jadi\s+)?makruh\s+',                     # "jadi makruh..."
            r'berarti\s+(boleh|tidak boleh)',           # "berarti boleh/tidak boleh"
            r'maka\s+(boleh|tidak boleh|halal|haram)', # "maka halal/haram"
            r'oleh\s+karena\s+itu\s+dilarang',          # "oleh karena itu dilarang"
            r'dengan\s+demikian\s+(halal|haram)',       # "dengan demikian halal/haram"
            r'kesimpulannya\s+(halal|haram|wajib)',     # "kesimpulannya haram"
        ]
        
        for pattern in forbidden_patterns:
            if re.search(pattern, answer_lower):
                claim_type = re.search(pattern, answer_lower).group(0)
                logger.warning(f"🚨 Forbidden claim pattern found: {claim_type}")
                
                return {
                    'has_forbidden_claim': True,
                    'claim_type': claim_type,
                    'pattern': pattern
                }
        
        return {
            'has_forbidden_claim': False,
            'claim_type': None,
            'pattern': None
        }
    
    def _create_safe_alternative(self, topic: str) -> str:
        """
        Buat alternative response yang aman untuk topik tertentu
        """
        
        if topic in self.FORBIDDEN_FATWA_TOPICS:
            return self.FORBIDDEN_FATWA_TOPICS[topic]['safe_response']
        
        return (
            "Pertanyaan Anda memerlukan pemahaman hukum Islam yang mendalam. "
            "Berikut sumber hadis yang relevan, tapi WAJIB dikonsultasikan dengan ulama terpercaya "
            "sebelum mengambil keputusan."
        )
    
    def get_stats(self) -> Dict:
        """
        Get statistics tentang validasi yang dilakukan
        """
        return {
            'total_checked': self.checked_count,
            'total_flagged': self.flagged_count,
            'flag_rate': f"{(self.flagged_count / max(self.checked_count, 1)) * 100:.1f}%"
        }

# Global instance
fatwa_guard = FatwaGuard()