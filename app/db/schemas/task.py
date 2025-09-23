from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from app.db.models.task import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    """Base schema for tasks."""
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    category_id: Optional[int] = None

    @validator('title')
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Task title cannot be empty')
        if len(v) > 200:
            raise ValueError('Task title cannot exceed 200 characters')
        return v

    @validator('description')
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 1000:
            raise ValueError('Task description cannot exceed 1000 characters')
        return v


class TaskCreate(TaskBase):
    """Schema for creating a task."""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    category_id: Optional[int] = None

    @validator('title')
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Task title cannot be empty')
            if len(v) > 200:
                raise ValueError('Task title cannot exceed 200 characters')
        return v

    @validator('description')
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 1000:
            raise ValueError('Task description cannot exceed 1000 characters')
        return v


class TaskResponse(TaskBase):
    """Schema for task response with metadata."""
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    is_overdue: bool

    class Config:
        from_attributes = True
