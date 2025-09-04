from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
import re


class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#6B7280"

    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Category name cannot be empty')
        if len(v) > 100:
            raise ValueError('Category name cannot exceed 100 characters')
        return v.strip()

    @validator('color')
    def validate_color(cls, v):
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color (e.g., #FF6B35)')
        return v


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('Category name cannot be empty')
            if len(v) > 100:
                raise ValueError('Category name cannot exceed 100 characters')
            return v.strip()
        return v

    @validator('color')
    def validate_color(cls, v):
        if v is not None and not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color (e.g., #FF6B35)')
        return v


class CategoryResponse(CategoryBase):
    id: int
    owner_id: int
    task_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True