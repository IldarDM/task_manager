from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, constr

from app.db.schemas.category import CategoryShort


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    archived = "archived"

class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"

class TaskBase(BaseModel):
    title: constr(min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None

class TaskCreate(TaskBase):
    due_date: Optional[datetime] = None
    category_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[constr(min_length=1, max_length=200)] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    category_id: Optional[int] = None

class TaskResponse(TaskBase):
    id: int
    owner_id: int
    category: Optional[CategoryShort] = None
    due_date: Optional[datetime] = None

    class Config:
        from_attributes = True