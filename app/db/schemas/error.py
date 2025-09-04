from pydantic import BaseModel
from typing import Any, Dict, Optional, List

class ErrorDetail(BaseModel):
    type: str
    message: str
    field: Optional[str] = None

class ErrorResponse(BaseModel):
    error: bool = True
    message: str
    details: Optional[List[ErrorDetail]] = None
    data: Optional[Dict[str, Any]] = None

class SuccessResponse(BaseModel):
    error: bool = False
    message: str
    data: Optional[Dict[str, Any]] = None