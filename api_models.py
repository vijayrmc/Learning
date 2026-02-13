from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class VideoProcessRequest(BaseModel):
    urls: List[str]

class VideoProcessResponse(BaseModel):
    success: bool
    modules_count: int
    errors: List[Dict[str, Any]]

class ReconstructionRequest(BaseModel):
    explanation: str

class TransferRequest(BaseModel):
    attempt: str

class SessionResponse(BaseModel):
    session_id: str
    status: str
    module_title: str
    current_step_data: Optional[Dict[str, Any]] = None
