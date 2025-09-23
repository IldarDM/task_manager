from pydantic import BaseModel
from typing import Any, Dict, Optional, List


class ErrorDetail(BaseModel):
    """Details of a specific error."""
    type: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    error: bool = True
    message: str
    details: Optional[List[ErrorDetail]] = None
    data: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    """Standard success response schema."""
    error: bool = False
    message: str
    data: Optional[Dict[str, Any]] = None
