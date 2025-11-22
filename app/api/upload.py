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
import os
import shutil

router = APIRouter()
pdf_processor = PDFProcessor()
chunker = HadisChunker()
embedding_service = EmbeddingService()

@router.post("/", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # Validasi
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    
    # Save file
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Extract PDF
        pdf_data = await pdf_processor.extract_text(file_path)
        
        # Create document record
        doc = HadisDocument(
            filename=file.filename,
            total_pages=pdf_data['total_pages'],
            status=DocumentStatus.PROCESSING
        )
        db.add(doc)
        await db.flush()
        
        # Process chunks
        for page_data in pdf_data['pages']:
            chunks = await chunker.chunk_text(
                page_data['text'],
                page_data['page_number']
            )
            
            # Generate embeddings dan save
            for chunk_data in chunks:
                embedding = await embedding_service.generate_embedding(chunk_data['text'])
                
                chunk = HadisChunk(
                    document_id=doc.id,
                    chunk_text=chunk_data['text'],
                    chunk_index=chunk_data['chunk_index'],
                    page_number=chunk_data['page_number'],
                    embedding=embedding,
                    metadata={}
                )
                db.add(chunk)
        
        # Update status
        doc.status = DocumentStatus.COMPLETED
        await db.commit()
        
        return UploadResponse(
            document_id=doc.id,
            filename=doc.filename,
            status=doc.status.value,
            upload_date=doc.upload_date,
            message="PDF berhasil diproses"
        )
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, f"Error processing PDF: {str(e)}")
    finally:
        os.remove(file_path)