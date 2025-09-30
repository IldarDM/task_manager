from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    """Schema for access/refresh token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None
