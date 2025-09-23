from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base schema for user information."""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str

    @validator('password')
    def validate_password(cls, v: str) -> str:
        from app.core.security import validate_password_strength
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError('; '.join(errors))
        return v


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login credentials."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response with metadata."""
    id: int
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    full_name: str

    class Config:
        from_attributes = True


class PasswordReset(BaseModel):
    """Schema for password reset."""
    email: EmailStr
    new_password: str

    @validator('new_password')
    def validate_password(cls, v: str) -> str:
        from app.core.security import validate_password_strength
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError('; '.join(errors))
        return v
