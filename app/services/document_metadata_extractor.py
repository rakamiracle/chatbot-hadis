import re
from typing import Dict, Optional
import fitz

class DocumentMetadataExtractor:
    """Extract metadata dari PDF hadis"""
    
    def __init__(self):
        self.kitab_patterns = [
            r'(?:Kitab|Shahih|Sahih|Sunan|Musnad|Muwaththa)\s+([A-Za-z\s]+)',
            r'(?:صحيح|سنن|مسند)\s+(\w+)',
        ]
        
        self.pengarang_patterns = [
            r'(?:Oleh|Karya|Penulis|Author)[:\s]+([A-Za-z\s\.]+)',
            r'(?:Imam|Syaikh|Sheikh)\s+([A-Za-z\s]+)',
        ]
        
        self.penerbit_patterns = [
            r'(?:Penerbit|Publisher)[:\s]+([A-Za-z\s]+)',
            r'(?:Diterbitkan oleh)[:\s]+([A-Za-z\s]+)',
        ]
    
    async def extract_from_pdf(self, pdf_path: str) -> Dict:
        """Extract metadata dari halaman awal PDF"""
        try:
            doc = fitz.open(pdf_path)
            
            # Ambil metadata dari PDF properties
            pdf_metadata = doc.metadata
            
            # Ekstrak text dari 5 halaman pertama
            first_pages_text = ""
            for i in range(min(5, len(doc))):
                first_pages_text += doc[i].get_text()
            
            doc.close()
            
            # Extract info
            metadata = {
                'kitab_name': self._extract_kitab(first_pages_text) or self._from_filename(pdf_path),
                'pengarang': self._extract_pengarang(first_pages_text) or pdf_metadata.get('author'),
                'penerbit': self._extract_penerbit(first_pages_text),
                'tahun_terbit': pdf_metadata.get('creationDate', '')[:4] if pdf_metadata.get('creationDate') else None,
                'pdf_title': pdf_metadata.get('title'),
                'pdf_subject': pdf_metadata.get('subject'),
                'pdf_keywords': pdf_metadata.get('keywords'),
            }
            
            return metadata
        
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            return {}
    
    def _extract_kitab(self, text: str) -> Optional[str]:
        """Extract nama kitab dari text"""
        for pattern in self.kitab_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                kitab = match.group(1).strip()
                # Clean up
                kitab = re.sub(r'\s+', ' ', kitab)
                if len(kitab) > 3 and len(kitab) < 100:
                    return kitab
        return None
    
    def _extract_pengarang(self, text: str) -> Optional[str]:
        """Extract nama pengarang"""
        for pattern in self.pengarang_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                pengarang = match.group(1).strip()
                if len(pengarang) > 3 and len(pengarang) < 100:
                    return pengarang
        return None
    
    def _extract_penerbit(self, text: str) -> Optional[str]:
        """Extract nama penerbit"""
        for pattern in self.penerbit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def _from_filename(self, pdf_path: str) -> Optional[str]:
        """Extract kitab name from filename"""
        import os
        filename = os.path.basename(pdf_path)
        # Remove extension
        name = os.path.splitext(filename)[0]
        # Clean common patterns
        name = re.sub(r'[-_]', ' ', name)
        name = re.sub(r'\d+', '', name)
        name = name.strip()
        
        if len(name) > 3:
            return name.title()
        return None