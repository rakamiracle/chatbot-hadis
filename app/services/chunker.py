class HadisChunker:
    def __init__(self, chunk_size=800, overlap=150):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    async def chunk_text(self, text: str, page_number: int):
        chunks = []
        for i, start in enumerate(range(0, len(text), self.chunk_size - self.overlap)):
            chunk = text[start:start + self.chunk_size].strip()
            if chunk:
                chunks.append({"text": chunk, "chunk_index": i, "page_number": page_number})
        return chunks