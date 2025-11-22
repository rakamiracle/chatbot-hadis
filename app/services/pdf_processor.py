import fitz

class PDFProcessor:
    async def extract_text(self, pdf_path: str):
        doc = fitz.open(pdf_path)
        pages = []
        for i in range(len(doc)):
            pages.append({"page_number": i + 1, "text": doc[i].get_text()})
        doc.close()
        return {"pages": pages, "total_pages": len(pages)}