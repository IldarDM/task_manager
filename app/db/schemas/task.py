from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from app.db.models.task import TaskStatus, TaskPriority


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    category_id: Optional[int] = None

    @validator('title')
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Task title cannot be empty')
        if len(v) > 200:
            raise ValueError('Task title cannot exceed 200 characters')
        return v.strip()

    @validator('description')
    def validate_description(cls, v):
        if v and len(v) > 1000:
            raise ValueError('Task description cannot exceed 1000 characters')
        return v


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    category_id: Optional[int] = None

    @validator('title')
    def validate_title(cls, v):
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('Task title cannot be empty')
            if len(v) > 200:
                raise ValueError('Task title cannot exceed 200 characters')
            return v.strip()
        return v

    @validator('description')
    def validate_description(cls, v):
        if v is not None and len(v) > 1000:
            raise ValueError('Task description cannot exceed 1000 characters')
        return v


class TaskResponse(TaskBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    is_overdue: bool

    class Config:
        from_attributes = True