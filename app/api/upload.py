from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.models.document import HadisDocument, DocumentStatus
from app.models.chunk import HadisChunk
from app.services.pdf_processor import PDFProcessor
from app.services.chunker import HadisChunker
from app.services.embedding_service import EmbeddingService
from app.schemas.upload import UploadResponse
from config import settings
import os, shutil

router = APIRouter()

@router.post("/", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF")
    
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    path = os.path.join(settings.UPLOAD_DIR, file.filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        pdf = PDFProcessor()
        chunker = HadisChunker()
        embed = EmbeddingService()
        
        data = await pdf.extract_text(path)
        doc = HadisDocument(filename=file.filename, total_pages=data['total_pages'])
        db.add(doc)
        await db.flush()
        
        for page in data['pages']:
            for chunk_data in await chunker.chunk_text(page['text'], page['page_number']):
                emb = await embed.generate_embedding(chunk_data['text'])
                chunk = HadisChunk(
                    document_id=doc.id,
                    chunk_text=chunk_data['text'],
                    chunk_index=chunk_data['chunk_index'],
                    page_number=chunk_data['page_number'],
                    embedding=emb,
                    chunk_metadata={}  # ← Ganti jadi chunk_metadata
                )
                db.add(chunk)
        
        doc.status = DocumentStatus.COMPLETED
        await db.commit()
        
        return UploadResponse(
            document_id=doc.id,
            filename=doc.filename,
            status=doc.status.value,
            upload_date=doc.upload_date
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, str(e))
    finally:
        os.remove(path)

        for page in data['pages']:
            for chunk_data in await chunker.chunk_text(page['text'], page['page_number']):
                emb = await embed.generate_embedding(chunk_data['text'])
                chunk = HadisChunk(
                    document_id=doc.id,
                    chunk_text=chunk_data['text'],
                    chunk_index=chunk_data['chunk_index'],
                    page_number=chunk_data['page_number'],
                    embedding=emb,
                    chunk_metadata=chunk_data.get('metadata', {})  # ← Simpan metadata
                )
                db.add(chunk)