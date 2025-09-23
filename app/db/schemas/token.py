from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """Schema for access token response."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for data stored in JWT token."""
    email: Optional[str] = None
