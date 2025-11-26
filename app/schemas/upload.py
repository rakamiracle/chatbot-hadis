from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UploadResponse(BaseModel):
    document_id: int
    filename: str
    status: str
    upload_date: datetime
    message: Optional[str] = "PDF berhasil diupload"