import re
from typing import List, Dict

class HadisChunker:
    def __init__(self, chunk_size=1000, overlap=200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    async def chunk_text(self, text: str, page_number: int) -> List[Dict]:
        """Chunk text dengan deteksi struktur hadis"""
        
        # Pattern untuk deteksi hadis (nomor hadis, perawi, dll)
        hadis_patterns = [
            r'\n\s*\d+\.\s*',  # Nomor hadis: "1. ", "123. "
            r'\n\s*Hadis\s+\d+',  # "Hadis 123"
            r'\n\s*HR\.\s*\w+',  # "HR. Bukhari"
            r'حَدَّثَنَا',  # Hadits Arab (haddatsana)
            r'عَنْ',  # Arab (an - dari)
        ]
        
        # Coba split berdasarkan pattern hadis
        chunks = self._smart_split(text, hadis_patterns)
        
        # Jika tidak ada pattern atau chunk terlalu besar, fallback ke character-based
        if not chunks or any(len(c) > self.chunk_size * 2 for c in chunks):
            chunks = self._fallback_split(text)
        
        result = []
        for i, chunk_text in enumerate(chunks):
            if chunk_text.strip():
                # Ekstrak metadata dari chunk
                metadata = self._extract_metadata(chunk_text)
                
                result.append({
                    "text": chunk_text.strip(),
                    "chunk_index": i,
                    "page_number": page_number,
                    "metadata": metadata
                })
        
        return result
    
    def _smart_split(self, text: str, patterns: List[str]) -> List[str]:
        """Split berdasarkan pattern hadis"""
        combined_pattern = '|'.join(patterns)
        
        # Split tapi keep delimiter
        parts = re.split(f'({combined_pattern})', text)
        
        chunks = []
        current_chunk = ""
        
        for part in parts:
            if len(current_chunk) + len(part) <= self.chunk_size:
                current_chunk += part
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = part
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _fallback_split(self, text: str) -> List[str]:
        """Fallback: split by character dengan overlap"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Cari pemisah natural (newline, titik, koma)
            if end < len(text):
                for sep in ['\n\n', '\n', '. ', '، ', ' ']:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep > self.chunk_size // 2:
                        end = start + last_sep + len(sep)
                        break
            
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            
            start = end - self.overlap
        
        return chunks
    
    def _extract_metadata(self, text: str) -> Dict:
        """Ekstrak metadata dari chunk (perawi, kitab, dll)"""
        metadata = {}
        
        # Deteksi perawi
        perawi_pattern = r'HR\.\s*(\w+)'
        match = re.search(perawi_pattern, text, re.IGNORECASE)
        if match:
            metadata['perawi'] = match.group(1)
        
        # Deteksi nomor hadis
        nomor_pattern = r'(?:Hadis|No)\s*[:\.]?\s*(\d+)'
        match = re.search(nomor_pattern, text, re.IGNORECASE)
        if match:
            metadata['nomor_hadis'] = match.group(1)
        
        # Deteksi derajat hadis
        derajat_keywords = ['shahih', 'hasan', 'dhaif', 'sahih', 'daif']
        for keyword in derajat_keywords:
            if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
                metadata['derajat'] = keyword
                break
        
        # Deteksi kitab
        kitab_pattern = r'(?:Shahih|Sahih|Sunan|Musnad)\s+(\w+)'
        match = re.search(kitab_pattern, text, re.IGNORECASE)
        if match:
            metadata['kitab'] = match.group(0)
        
        return metadata