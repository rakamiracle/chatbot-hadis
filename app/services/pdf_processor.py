import fitz
from typing import Dict, List

class PDFProcessor:
    async def extract_text(self, pdf_path: str) -> Dict:
        doc = fitz.open(pdf_path)
        
        full_text = ""
        pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            full_text += text + "\n"
            pages.append({
                "page_number": page_num + 1,
                "text": text
            })
        
        doc.close()
        
        return {
            "full_text": full_text,
            "pages": pages,
            "total_pages": len(pages)
        }