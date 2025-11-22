from pydantic import BaseModel
from datetime import datetime

class UploadResponse(BaseModel):
    document_id: int
    filename: str
    status: str
    upload_date: datetime