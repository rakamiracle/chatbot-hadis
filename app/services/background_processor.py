import asyncio
from typing import Dict, Callable
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class BackgroundJobManager:
    """Simple background job manager"""
    
    def __init__(self):
        self.jobs: Dict[str, Dict] = {}
    
    def create_job(self, job_id: str, job_type: str) -> Dict:
        """Create new background job"""
        job = {
            "id": job_id,
            "type": job_type,
            "status": JobStatus.PENDING,
            "progress": 0,
            "message": "Job created",
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "result": None
        }
        self.jobs[job_id] = job
        return job
    
    def update_job(self, job_id: str, **kwargs):
        """Update job status"""
        if job_id in self.jobs:
            self.jobs[job_id].update(kwargs)
    
    def get_job(self, job_id: str) -> Dict:
        """Get job status"""
        return self.jobs.get(job_id)
    
    async def run_job(self, job_id: str, task: Callable, *args, **kwargs):
        """Run job asynchronously"""
        self.update_job(
            job_id,
            status=JobStatus.PROCESSING,
            started_at=datetime.utcnow().isoformat(),
            message="Processing..."
        )
        
        try:
            result = await task(*args, **kwargs, job_id=job_id)
            
            self.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                completed_at=datetime.utcnow().isoformat(),
                message="Completed successfully",
                result=result
            )
        except Exception as e:
            self.update_job(
                job_id,
                status=JobStatus.FAILED,
                completed_at=datetime.utcnow().isoformat(),
                message="Failed",
                error=str(e)
            )

# Global job manager instance
job_manager = BackgroundJobManager()