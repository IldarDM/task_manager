from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_validator, constr

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

def _normalize_enum_value(v: str) -> str:
    if v is None:
        return v
    s = str(v).strip().lower().replace("-", "_")
    aliases = {"inprogress": "in_progress", "in progress": "in_progress"}
    return aliases.get(s, s)

class TaskBase(BaseModel):
    title: constr(min_length=1, max_length=200)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium

    @field_validator("status", mode="before")
    @classmethod
    def _status_any_case(cls, v):
        if isinstance(v, TaskStatus) or v is None:
            return v
        return _normalize_enum_value(v)

    @field_validator("priority", mode="before")
    @classmethod
    def _priority_any_case(cls, v):
        if isinstance(v, TaskPriority) or v is None:
            return v
        return _normalize_enum_value(v)

class TaskCreate(TaskBase):
    due_date: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[constr(min_length=1, max_length=200)] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def _status_any_case_u(cls, v):
        if isinstance(v, TaskStatus) or v is None:
            return v
        return _normalize_enum_value(v)

    @field_validator("priority", mode="before")
    @classmethod
    def _priority_any_case_u(cls, v):
        if isinstance(v, TaskPriority) or v is None:
            return v
        return _normalize_enum_value(v)

class TaskResponse(TaskBase):
    id: int
    owner_id: int
    category_id: Optional[int] = None
    class Config:
        from_attributes = True
