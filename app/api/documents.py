from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.database.connection import get_db
from app.models.document import HadisDocument
from app.models.chunk import HadisChunk
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

class DocumentInfo(BaseModel):
    id: int
    filename: str
    kitab_name: Optional[str]
    pengarang: Optional[str]
    total_pages: int
    total_chunks: int
    status: str
    upload_date: str

class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentInfo]

@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    kitab: Optional[str] = Query(None, description="Filter by kitab name"),
    pengarang: Optional[str] = Query(None, description="Filter by pengarang"),
    search: Optional[str] = Query(None, description="Search in filename/kitab/pengarang"),
    db: AsyncSession = Depends(get_db)
):
    """List semua dokumen dengan filter"""
    
    query = select(HadisDocument)
    
    # Apply filters
    if kitab:
        query = query.where(HadisDocument.kitab_name.ilike(f"%{kitab}%"))
    
    if pengarang:
        query = query.where(HadisDocument.pengarang.ilike(f"%{pengarang}%"))
    
    if search:
        query = query.where(
            or_(
                HadisDocument.filename.ilike(f"%{search}%"),
                HadisDocument.kitab_name.ilike(f"%{search}%"),
                HadisDocument.pengarang.ilike(f"%{search}%")
            )
        )
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    # Get chunk counts
    doc_infos = []
    for doc in documents:
        chunk_count = await db.scalar(
            select(func.count(HadisChunk.id)).where(HadisChunk.document_id == doc.id)
        )
        
        doc_infos.append(DocumentInfo(
            id=doc.id,
            filename=doc.filename,
            kitab_name=doc.kitab_name,
            pengarang=doc.pengarang,
            total_pages=doc.total_pages,
            total_chunks=chunk_count or 0,
            status=doc.status.value,
            upload_date=doc.upload_date.isoformat()
        ))
    
    return DocumentListResponse(
        total=len(doc_infos),
        documents=doc_infos
    )

@router.get("/{document_id}")
async def get_document_detail(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detail dokumen tertentu"""
    result = await db.execute(
        select(HadisDocument).where(HadisDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    # Get chunk count
    chunk_count = await db.scalar(
        select(func.count(HadisChunk.id)).where(HadisChunk.document_id == doc.id)
    )
    
    # Sample chunks
    chunks_result = await db.execute(
        select(HadisChunk)
        .where(HadisChunk.document_id == doc.id)
        .limit(5)
    )
    sample_chunks = chunks_result.scalars().all()
    
    return {
        "id": doc.id,
        "filename": doc.filename,
        "kitab_name": doc.kitab_name,
        "pengarang": doc.pengarang,
        "penerbit": doc.penerbit,
        "tahun_terbit": doc.tahun_terbit,
        "total_pages": doc.total_pages,
        "total_chunks": chunk_count,
        "status": doc.status.value,
        "upload_date": doc.upload_date.isoformat(),
        "doc_metadata": doc.doc_metadata,
        "sample_chunks": [
            {
                "page": c.page_number,
                "text": c.chunk_text[:200],
                "metadata": c.chunk_metadata
            }
            for c in sample_chunks
        ]
    }

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Hapus dokumen dan semua chunks-nya"""
    result = await db.execute(
        select(HadisDocument).where(HadisDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(404, "Document not found")
    
    await db.delete(doc)
    await db.commit()
    
    return {"message": f"Document {doc.filename} deleted successfully"}

@router.get("/kitab/list")
async def list_kitab(db: AsyncSession = Depends(get_db)):
    """List semua kitab yang ada"""
    result = await db.execute(
        select(HadisDocument.kitab_name, func.count(HadisDocument.id))
        .where(HadisDocument.kitab_name.isnot(None))
        .group_by(HadisDocument.kitab_name)
    )
    
    kitab_list = [
        {"kitab": name, "document_count": count}
        for name, count in result.all()
    ]
    
    return {"kitab": kitab_list}