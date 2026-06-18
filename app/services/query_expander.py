"""
🔥 NEW: Query Expansion Service
Memperluas generic queries menjadi lebih spesifik untuk vector search
"""

from typing import List, Dict
from app.utils.logger import logger
import re

class QueryExpander:
    """Expand vague/generic queries ke bentuk yang lebih searchable"""
    
    # Islamic concept mappings
    CONCEPT_MAPPINGS = {
        'islam': ['iman', 'tauhid', 'syahadat', 'ibadah', 'doa', 'shalat'],
        'pacaran': ['hubungan', 'pemuda', 'wanita', 'laki-laki', 'pergaulan', 'zina'],
        'puasa': ['ramadhan', 'shaum', 'berpuasa', 'berbuka', 'sahur'],
        'shalat': ['salat', 'solat', 'sembahyang', 'shalat lima', 'thayyib'],
        'zakat': ['sedekah', 'infaq', 'harta', 'kaya', 'miskin'],
        'haji': ['umroh', 'ihram', 'tawaf', 'sa\'i', 'makkah'],
        'wudhu': ['bersuci', 'thaharah', 'air', 'niat'],
        'akhlak': ['perilaku', 'kepribadian', 'karakter', 'etika', 'moral'],
        'pernikahan': ['nikah', 'kawin', 'istri', 'suami', 'mahr', 'ijab'],
        'hukum': ['halal', 'haram', 'wajib', 'sunnah', 'makruh', 'fatwa'],
        'doa': ['dzikir', 'wirid', 'do\'a', 'munajat'],
    }
    
    # Query patterns untuk detect intent
    QUERY_PATTERNS = {
        'definition': r'^(apa|apa itu|jelaskan|definisi|pengertian)',
        'how_to': r'^(bagaimana|cara|tata cara|prosedur)',
        'why': r'^(kenapa|mengapa|alasan)',
        'who': r'^(siapa|nama)',
        'ruling': r'^(boleh|halal|haram|wajib)',
        'hadis': r'hadis|riwayat|diriwayatkan',
    }
    
    def __init__(self):
        self.concept_map = self.CONCEPT_MAPPINGS
    
    def expand_query(self, query: str) -> Dict[str, any]:
        """
        Expand query dengan menambahkan related keywords
        
        Returns:
        {
            'original': 'apa itu islam?',
            'intent': 'definition',
            'expanded': 'islam iman tauhid syahadat ibadah',
            'keywords': ['islam', 'iman', 'tauhid', 'syahadat', 'ibadah'],
            'suggestions': ['Jelaskan tentang iman', 'Apa bedanya...']
        }
        """
        
        query_clean = query.lower().strip('?.,!')
        intent = self._detect_intent(query)
        
        # Extract main keywords
        keywords = self._extract_main_keywords(query_clean)
        
        # Expand with related concepts
        expanded_keywords = set(keywords)
        for keyword in keywords:
            if keyword in self.concept_map:
                expanded_keywords.update(self.concept_map[keyword])
        
        expanded_query = ' '.join(expanded_keywords)
        
        logger.debug(f"Query Expansion: '{query}' -> {expanded_keywords}")
        
        return {
            'original': query,
            'intent': intent,
            'expanded': expanded_query,
            'keywords': list(expanded_keywords),
            'primary_keyword': keywords[0] if keywords else None,
            'related_concepts': [k for k in expanded_keywords if k not in keywords]
        }
    
    def _detect_intent(self, query: str) -> str:
        """Detect query intent"""
        query_lower = query.lower()
        
        for intent, pattern in self.QUERY_PATTERNS.items():
            if re.search(pattern, query_lower):
                return intent
        
        return 'general'
    
    def _extract_main_keywords(self, query: str) -> List[str]:
        """Extract main keywords dari query"""
        
        # Remove question words
        question_words = ['apa', 'apa itu', 'jelaskan', 'bagaimana', 'kenapa', 'mengapa', 
                         'siapa', 'kapan', 'dimana', 'berapa', 'definisi', 'pengertian']
        
        words = re.findall(r'\b\w+\b', query.lower())
        
        keywords = [w for w in words if w not in question_words and len(w) > 2]
        
        return keywords[:3]  # Return top 3 keywords
    
    def get_fallback_suggestions(self, query: str) -> List[str]:
        """Generate fallback search suggestions"""
        expansion = self.expand_query(query)
        primary = expansion['primary_keyword']
        
        if not primary:
            return []
        
        suggestions = []
        
        # Suggestion 1: More specific
        if expansion['intent'] == 'definition':
            suggestions.append(f"Jelaskan tentang {primary}")
        
        # Suggestion 2: Related concepts
        if expansion['related_concepts']:
            related = expansion['related_concepts'][0]
            suggestions.append(f"Apa itu {related}?")
        
        # Suggestion 3: Hadis spesifik
        suggestions.append(f"Hadis tentang {primary}")
        
        return suggestions[:3]

# Global instance
query_expander = QueryExpander()