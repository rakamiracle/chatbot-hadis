import re
# HAPUS: from typing import str

class HadisTextCleaner:
    """Advanced text cleaning untuk hadis"""
    
    def __init__(self):
        # Arabic diacritics (harakat)
        self.arabic_diacritics = re.compile(r'[\u064B-\u065F\u0670]')
        
        # Tatweel (kashida)
        self.tatweel = re.compile(r'\u0640')
    
    def clean(self, text: str, preserve_arabic: bool = True) -> str:
        """Deep cleaning text"""
        
        # 1. Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # 2. Remove control characters
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # 3. Arabic specific cleaning
        if preserve_arabic:
            # Remove harakat tapi keep text
            text = self.arabic_diacritics.sub('', text)
            
            # Remove tatweel
            text = self.tatweel.sub('', text)
            
            # Normalize Arabic letters
            text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
            text = text.replace('ة', 'ه')
            text = text.replace('ى', 'ي')
        
        # 4. Remove extra punctuation
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r',{2,}', ',', text)
        
        # 5. Fix common OCR errors
        text = text.replace('‐', '-')
        text = text.replace('–', '-')
        text = text.replace('—', '-')
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # 6. Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # 7. Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        return text.strip()
    
    def normalize_hadis_numbering(self, text: str) -> str:
        """Normalize format nomor hadis"""
        # Standardize hadis numbering
        text = re.sub(r'(?:Hadis|Hadits|HR)[:\.]?\s*No[:\.]?\s*(\d+)', r'Hadis \1', text, flags=re.IGNORECASE)
        text = re.sub(r'(?:Nomor|No)[:\.]?\s*(\d+)', r'Hadis \1', text, flags=re.IGNORECASE)
        
        return text
    
    def extract_clean_hadis(self, text: str) -> str:
        """Extract dan clean hadis specific content"""
        # Clean
        text = self.clean(text)
        
        # Normalize numbering
        text = self.normalize_hadis_numbering(text)
        
        # Remove common headers/footers
        text = re.sub(r'Halaman\s+\d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Page\s+\d+', '', text, flags=re.IGNORECASE)
        
        return text.strip()