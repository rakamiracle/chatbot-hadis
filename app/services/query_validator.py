from app.utils.logger import logger
from typing import Dict, Optional

class QueryValidator:
    """Validasi query sebelum diproses - Safety layer untuk pertanyaan sensitif"""
    
    # 🔥 Topic sensitif dengan level severity
    SENSITIVE_TOPICS = {
        # Level CRITICAL - Hukum/Fatwa yang butuh konsultasi ulama
        'hukum': 'critical',
        'halal': 'critical',
        'haram': 'critical',
        'wajib': 'critical',
        'sunnah': 'critical',
        'makruh': 'critical',
        'mubah': 'critical',
        'fatwa': 'critical',
        
        # Level HIGH - Topik keluarga dan transaksi
        'nikah': 'high',
        'talak': 'high',
        'cerai': 'high',
        'warisan': 'high',
        'riba': 'high',
        'jual beli': 'high',
        'hutang': 'high',
        
        # Level MEDIUM - Ibadah dan perilaku
        'boleh': 'medium',
        'dilarang': 'medium',
        'pacaran': 'medium',
        'musik': 'medium',
        'foto': 'medium',
        'gambar': 'medium',
    }
    
    # 🔥 Kata kunci yang membutuhkan warning khusus
    MEDICAL_KEYWORDS = ['obat', 'penyakit', 'sakit', 'pengobatan', 'ruqyah', 'thibbun nabawi']
    LEGAL_KEYWORDS = ['hukuman', 'pidana', 'had', 'qisas', 'ta\'zir']
    
    def __init__(self):
        self.validation_count = 0
        self.sensitive_count = 0
    
    def validate_query(self, query: str) -> Dict[str, any]:
        """
        Validasi query dan return status
        
        Returns:
            {
                'is_valid': bool,
                'is_sensitive': bool,
                'severity': str or None,
                'disclaimer': str or None,
                'topics_detected': list
            }
        """
        self.validation_count += 1
        query_lower = query.lower()
        
        # Check panjang query
        if len(query.strip()) < 3:
            return {
                'is_valid': False,
                'is_sensitive': False,
                'severity': None,
                'disclaimer': None,
                'topics_detected': [],
                'error': 'Query terlalu pendek'
            }
        
        # Detect sensitive topics
        detected_topics = []
        max_severity = None
        
        for topic, severity in self.SENSITIVE_TOPICS.items():
            if topic in query_lower:
                detected_topics.append(topic)
                if max_severity is None or self._compare_severity(severity, max_severity) > 0:
                    max_severity = severity
        
        is_sensitive = len(detected_topics) > 0
        
        if is_sensitive:
            self.sensitive_count += 1
            logger.warning(f"Sensitive query detected (severity: {max_severity}): {query[:50]}...")
        
        # Get appropriate disclaimer
        disclaimer = self._get_disclaimer(max_severity, query_lower) if is_sensitive else None
        
        return {
            'is_valid': True,
            'is_sensitive': is_sensitive,
            'severity': max_severity,
            'disclaimer': disclaimer,
            'topics_detected': detected_topics
        }
    
    def is_sensitive(self, query: str) -> bool:
        """Check if query tentang topik sensitif (backward compatibility)"""
        result = self.validate_query(query)
        return result['is_sensitive']
    
    def get_disclaimer(self, query: Optional[str] = None) -> str:
        """Get disclaimer (backward compatibility)"""
        if query:
            result = self.validate_query(query)
            return result['disclaimer'] if result['disclaimer'] else self._get_general_disclaimer()
        return self._get_general_disclaimer()
    
    def _compare_severity(self, severity1: str, severity2: str) -> int:
        """Compare severity levels. Return 1 if severity1 > severity2, -1 if <, 0 if =="""
        levels = {'critical': 3, 'high': 2, 'medium': 1}
        return levels.get(severity1, 0) - levels.get(severity2, 0)
    
    def _get_disclaimer(self, severity: Optional[str], query_lower: str) -> str:
        """Get disclaimer berdasarkan severity dan context"""
        
        # Check medical context
        if any(kw in query_lower for kw in self.MEDICAL_KEYWORDS):
            return (
                "\n\n⚠️ **DISCLAIMER MEDIS**: "
                "Informasi ini hanya referensi hadis, BUKAN nasihat medis. "
                "Untuk masalah kesehatan, konsultasikan dengan dokter profesional. "
                "Jangan hanya mengandalkan pengobatan alternatif tanpa konsultasi medis."
            )
        
        # Check legal context
        if any(kw in query_lower for kw in self.LEGAL_KEYWORDS):
            return (
                "\n\n⚠️ **DISCLAIMER HUKUM**: "
                "Ini referensi teks hadis, BUKAN fatwa atau keputusan hukum. "
                "Hukum Islam diterapkan oleh ulama kompeten dengan mempertimbangkan konteks. "
                "Konsultasikan dengan ulama atau lembaga fatwa resmi."
            )
        
        # Default based on severity
        if severity == 'critical':
            return (
                "\n\n⚠️ **PENTING - DISCLAIMER FATWA**: "
                "Jawaban ini HANYA referensi teks hadis, BUKAN fatwa resmi. "
                "Hukum Islam memerlukan analisis mendalam oleh ulama yang kompeten. "
                "**WAJIB konsultasi dengan ulama terpercaya untuk pengamalan hukum.**"
            )
        elif severity == 'high':
            return (
                "\n\n⚠️ **CATATAN PENTING**: "
                "Ini hanya referensi hadis, bukan nasihat hukum yang mengikat. "
                "Untuk keputusan penting (nikah, talak, warisan, dll), "
                "**konsultasikan dengan ulama atau lembaga fatwa resmi.**"
            )
        else:  # medium
            return self._get_general_disclaimer()
    
    def _get_general_disclaimer(self) -> str:
        """General disclaimer untuk semua query sensitif"""
        return (
            "\n\n⚠️ **CATATAN**: "
            "Ini referensi teks hadis, bukan fatwa resmi. "
            "Untuk panduan hukum, konsultasikan dengan ulama terpercaya."
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics"""
        return {
            'total_validations': self.validation_count,
            'sensitive_queries': self.sensitive_count,
            'normal_queries': self.validation_count - self.sensitive_count
        }

# Singleton instance
query_validator = QueryValidator()