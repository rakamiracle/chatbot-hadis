from typing import List, Dict

class HadisChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    async def chunk_text(self, text: str, page_number: int = 1) -> List[Dict]:
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]
            
            if chunk_text.strip():
                chunks.append({
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "page_number": page_number
                })
                chunk_index += 1
            
            start = end - self.chunk_overlap
        
        return chunks