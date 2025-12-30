from pydantic import BaseModel
from typing import List, Optional

class JobSubmit(BaseModel):
    analysis_type: str
    parameters: dict

class JobStatus(BaseModel):
    job_id: str
    status: str
    result: Optional[dict] = None