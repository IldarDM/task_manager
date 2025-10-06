import re

from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    """Base schema for categories."""
    name: str
    description: Optional[str] = None
    color: str = "#6B7280"

    @validator('name')
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Category name cannot be empty')
        if len(v) > 100:
            raise ValueError('Category name cannot exceed 100 characters')
        return v

    @validator('color')
    def validate_color(cls, v: str) -> str:
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color (e.g., #FF6B35)')
        return v


class CategoryCreate(CategoryBase):
    """Schema for creating a category."""
    pass


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None

    @validator('name')
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Category name cannot be empty')
            if len(v) > 100:
                raise ValueError('Category name cannot exceed 100 characters')
        return v

    @validator('color')
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color (e.g., #FF6B35)')
        return v


class CategoryResponse(CategoryBase):
    """Schema for category response with metadata."""
    id: int
    owner_id: int
    task_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CategoryShort(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True