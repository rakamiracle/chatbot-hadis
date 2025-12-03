from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.models.document import HadisDocument, DocumentStatus
from app.models.chunk import HadisChunk
from app.services.pdf_processor import PDFProcessor
from app.services.chunker import HadisChunker
from app.services.embedding_service import EmbeddingService
from app.services.document_metadata_extractor import DocumentMetadataExtractor
from app.services.text_cleaner import HadisTextCleaner
from app.services.pdf_validator import PDFValidator
from app.schemas.upload import UploadResponse
from app.utils.logger import logger, log_upload
from config import settings
import os
import shutil
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload PDF with validation"""
    
    start_time = datetime.utcnow()
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(settings.UPLOAD_DIR, temp_filename)
    
    try:
        # Save file
        with open(path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        logger.info(f"File uploaded: {file.filename} ({os.path.getsize(path) / 1024 / 1024:.2f}MB)")
        
        # Validate PDF
        validator = PDFValidator()
        validation_result = await validator.validate(path)
        
        if not validation_result['valid']:
            logger.error(f"PDF validation failed: {validation_result['errors']}")
            os.remove(path)
            raise HTTPException(400, f"PDF validation failed: {', '.join(validation_result['errors'])}")
        
        if validation_result.get('warnings'):
            logger.warning(f"PDF warnings: {validation_result['warnings']}")
        
        # Create document
        doc = HadisDocument(
            filename=file.filename,
            status=DocumentStatus.PROCESSING
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        logger.info(f"Document created with ID: {doc.id}")
        
        # Process PDF
        await process_pdf_sync(path, doc.id, db, file.filename)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        log_upload(file.filename, "success", duration)
        
        return UploadResponse(
            document_id=doc.id,
            filename=file.filename,
            status="completed",
            upload_date=doc.upload_date,
            message="PDF berhasil diproses"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        duration = (datetime.utcnow() - start_time).total_seconds()
        log_upload(file.filename, "error", duration, str(e))
        raise HTTPException(500, f"Error: {str(e)}")

async def process_pdf_sync(pdf_path: str, doc_id: int, db: AsyncSession, filename: str):
    """Process PDF synchronously with optimization"""
    try:
        from sqlalchemy import select
        
        # Services
        pdf = PDFProcessor()
        chunker = HadisChunker()
        embed = EmbeddingService()
        meta_extractor = DocumentMetadataExtractor()
        cleaner = HadisTextCleaner()
        
        logger.info(f"[{doc_id}] Extracting metadata...")
        doc_metadata = await meta_extractor.extract_from_pdf(pdf_path)
        
        logger.info(f"[{doc_id}] Extracting text...")
        data = await pdf.extract_text(pdf_path)
        
        # Update document
        result = await db.execute(select(HadisDocument).where(HadisDocument.id == doc_id))
        doc = result.scalar_one()
        
        doc.total_pages = data['total_pages']
        doc.kitab_name = doc_metadata.get('kitab_name')
        doc.pengarang = doc_metadata.get('pengarang')
        doc.penerbit = doc_metadata.get('penerbit')
        doc.tahun_terbit = doc_metadata.get('tahun_terbit')
        doc.doc_metadata = doc_metadata
        await db.commit()
        
        logger.info(f"[{doc_id}] Processing {data['total_pages']} pages...")
        
        # Collect chunks
        all_chunks = []
        for page in data['pages']:
            cleaned_text = cleaner.extract_clean_hadis(page['text'])
            chunks = await chunker.chunk_text(cleaned_text, page['page_number'])
            all_chunks.extend(chunks)
        
        logger.info(f"[{doc_id}] Generated {len(all_chunks)} chunks")
        
        # Batch embedding
        logger.info(f"[{doc_id}] Generating embeddings...")
        batch_size = 50
        chunk_objects = []
        
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            texts = [c['text'] for c in batch]
            embeddings = await embed.generate_embeddings_batch(texts)
            
            for chunk_data, embedding in zip(batch, embeddings):
                chunk = HadisChunk(
                    document_id=doc.id,
                    chunk_text=chunk_data['text'],
                    chunk_index=chunk_data['chunk_index'],
                    page_number=chunk_data['page_number'],
                    embedding=embedding,
                    chunk_metadata=chunk_data.get('metadata', {})
                )
                chunk_objects.append(chunk)
            
            logger.info(f"[{doc_id}] Processed {min(i+batch_size, len(all_chunks))}/{len(all_chunks)} chunks")
        
        # Bulk insert
        logger.info(f"[{doc_id}] Saving to database...")
        db.add_all(chunk_objects)
        
        # Generate document-level embedding
        logger.info(f"[{doc_id}] Generating document-level embedding...")
        try:
            # Create document summary from first 5 chunks (or all if less than 5)
            summary_chunks = all_chunks[:min(5, len(all_chunks))]
            summary_text = " ".join([chunk['text'] for chunk in summary_chunks])
            
            # Truncate to reasonable length (max ~512 tokens ≈ 2000 chars)
            if len(summary_text) > 2000:
                summary_text = summary_text[:2000]
            
            # Generate embedding for document summary
            doc_embedding = await embed.generate_embedding(summary_text)
            
            # Update document with summary and embedding
            doc.summary_text = summary_text
            doc.embedding = doc_embedding
            
            logger.info(f"[{doc_id}] ✓ Document embedding generated")
        except Exception as e:
            logger.warning(f"[{doc_id}] Failed to generate document embedding: {e}")
            # Continue even if document embedding fails
        
        # Update status
        doc.status = DocumentStatus.COMPLETED
        await db.commit()
        await db.refresh(doc)
        
        logger.info(f"[{doc_id}] ✓ COMPLETED - {len(chunk_objects)} chunks saved, status: {doc.status}")
        
        return {"document_id": doc_id, "chunks_created": len(chunk_objects)}
    
    except Exception as e:
        logger.error(f"[{doc_id}] Processing error: {str(e)}", exc_info=True)
        
        from sqlalchemy import select
        result = await db.execute(select(HadisDocument).where(HadisDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = DocumentStatus.FAILED
            await db.commit()
        
        raise
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            logger.info(f"[{doc_id}] Temp file deleted")