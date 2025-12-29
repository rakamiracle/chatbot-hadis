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
            r'\n\s*Bab\s+\d+',  # "Bab 5"
            r'\n\s*Bab\s*:',  # "Bab: ..."
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
        """Ekstrak metadata dari chunk - IMPROVED VERSION"""
        metadata = {}
        
        # 🔥 1. Deteksi KITAB dengan pattern lebih lengkap
        kitab_patterns = [
            r'(?:Shahih|Sahih|Sunan|Musnad|Muwaththa|Muwatta)\s+([A-Za-z\s]+?)(?=\s*(?:Bab|Hadis|HR|No|\d+|$))',
            r'(?:صحيح|سنن|مسند|موطأ)\s+(\w+)',
            r'Kitab\s+([A-Za-z\s]+?)(?=\s*(?:Bab|Hadis|HR|No|\d+|$))',
        ]
        for pattern in kitab_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                kitab = match.group(1).strip()
                # Clean up
                kitab = re.sub(r'\s+', ' ', kitab)
                # Remove trailing words
                kitab = re.sub(r'\s+(Bab|Hadis|HR|No).*', '', kitab, flags=re.IGNORECASE)
                if len(kitab) > 3 and len(kitab) < 50:
                    metadata['kitab'] = kitab
                    break
        
        # 🔥 2. Deteksi BAB dengan pattern lebih kuat
        bab_patterns = [
            r'Bab\s+(\d+)\s*[:\-]?\s*([^\n]{10,100})',  # "Bab 5: Tentang Shalat"
            r'Bab\s*[:\-]\s*([^\n]{10,100})',  # "Bab: Tentang Shalat"
            r'(?:باب|الباب)\s*[:\-]?\s*([^\n]{10,100})',  # Arab
        ]
        for pattern in bab_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    bab_num, bab_title = match.groups()
                    metadata['bab_nomor'] = bab_num
                    metadata['bab'] = bab_title.strip()
                else:
                    metadata['bab'] = match.group(1).strip()
                break
        
        # 🔥 3. Deteksi NOMOR HADIS dengan pattern lengkap
        nomor_patterns = [
            r'Hadis\s+(?:No\.?|Nomor)?\s*[:\-]?\s*(\d+)',
            r'(?:No|Nomor)\s*[:\.]?\s*(\d+)',
            r'HR\.\s*\w+\s+No\.\s*(\d+)',
            r'^\s*(\d+)\.\s+',  # Nomor di awal baris
        ]
        for pattern in nomor_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                metadata['nomor_hadis'] = match.group(1)
                break
        
        # 🔥 4. Deteksi PERAWI
        perawi_patterns = [
            r'HR\.\s*(\w+(?:\s+\w+)?)',
            r'Diriwayatkan\s+oleh\s+(\w+)',
            r'Riwayat\s+(\w+)',
        ]
        for pattern in perawi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                perawi = match.group(1).strip()
                if perawi and len(perawi) < 50:
                    metadata['perawi'] = perawi
                    break
        
        # 🔥 5. Deteksi DERAJAT hadis
        derajat_keywords = ['shahih', 'hasan', 'dhaif', 'sahih', 'daif', 'muttafaq']
        for keyword in derajat_keywords:
            if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
                metadata['derajat'] = keyword.capitalize()
                break
        
        # 🔥 6. Ekstrak teks Arab (untuk ditampilkan terpisah)
        arabic_pattern = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+'
        arabic_matches = re.findall(arabic_pattern, text)
        
        if arabic_matches:
            # Ambil teks Arab terpanjang (biasanya itu hadis utama)
            longest_arabic = max(arabic_matches, key=len)
            if len(longest_arabic) > 20:  # Minimal 20 karakter
                metadata['arab'] = longest_arabic
        
        return metadata