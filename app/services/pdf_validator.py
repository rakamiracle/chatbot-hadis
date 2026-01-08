import fitz
from typing import Dict, List
import os

class PDFValidator:
    """Validate PDF quality sebelum processing"""
    
    def __init__(self):
        self.min_pages = 1
        self.max_pages = 2000
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.min_text_ratio = 0.1  # Min 10% halaman harus ada text
    
    async def validate(self, pdf_path: str) -> Dict:
        """Comprehensive PDF validation"""
        errors = []
        warnings = []
        
        # 1. File exists and readable
        if not os.path.exists(pdf_path):
            errors.append("File tidak ditemukan")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # 2. File size check
        file_size = os.path.getsize(pdf_path)
        if file_size > self.max_file_size:
            errors.append(f"File terlalu besar ({file_size / 1024 / 1024:.1f}MB). Maksimal 100MB")
        
        if file_size < 1024:  # Less than 1KB
            errors.append("File terlalu kecil, mungkin corrupt")
        
        try:
            doc = fitz.open(pdf_path)
            
            # 3. Page count validation
            page_count = len(doc)
            if page_count < self.min_pages:
                errors.append("PDF tidak memiliki halaman")
            elif page_count > self.max_pages:
                warnings.append(f"PDF memiliki {page_count} halaman, processing mungkin lama")
            
            # 4. Check if encrypted
            if doc.is_encrypted:
                errors.append("PDF terenkripsi/password-protected")
            
            # 5. Text extraction quality check
            pages_with_text = 0
            total_text_length = 0
            
            # Sample beberapa halaman
            sample_pages = min(10, page_count)
            for i in range(0, page_count, max(1, page_count // sample_pages)):
                text = doc[i].get_text()
                total_text_length += len(text)
                if len(text.strip()) > 50:  # Halaman dengan text meaningful
                    pages_with_text += 1
            
            text_ratio = pages_with_text / sample_pages
            
            if text_ratio < self.min_text_ratio:
                warnings.append(
                    f"PDF mungkin hasil scan/gambar. Hanya {int(text_ratio * 100)}% halaman memiliki text. "
                    "Hasil ekstraksi mungkin tidak optimal."
                )
            
            # 6. Average text per page
            avg_text_per_page = total_text_length / sample_pages
            if avg_text_per_page < 100:
                warnings.append("PDF memiliki sedikit text per halaman, mungkin hasil scan berkualitas rendah")
            
            # 7. Check metadata
            metadata = doc.metadata
            
            doc.close()
            
            # 8. Build result
            result = {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "info": {
                    "page_count": page_count,
                    "file_size_mb": round(file_size / 1024 / 1024, 2),
                    "text_ratio": round(text_ratio * 100, 1),
                    "avg_text_per_page": int(avg_text_per_page),
                    "has_metadata": bool(metadata.get('title') or metadata.get('author')),
                    "encrypted": doc.is_encrypted if 'doc' in locals() else False
                }
            }
            
            return result
        
        except Exception as e:
            errors.append(f"Error membaca PDF: {str(e)}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "info": {}
            }