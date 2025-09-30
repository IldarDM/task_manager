from enum import Enum
from typing import Optional
from datetime import datetime, date, time

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


def _as_datetime(v) -> Optional[datetime]:
    """Приводит разные представления к datetime (локально без TZ)."""
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime.combine(v, time(0, 0, 0))
    s = str(v).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s)
    except Exception:
        raise ValueError("Invalid due_date format")


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
        return TaskStatus(_normalize_enum_value(v))

    @field_validator("priority", mode="before")
    @classmethod
    def _priority_any_case(cls, v):
        if isinstance(v, TaskPriority) or v is None:
            return v
        return TaskPriority(_normalize_enum_value(v))


class TaskCreate(TaskBase):
    due_date: Optional[datetime] = None

    @field_validator("due_date", mode="before")
    @classmethod
    def _due_any_format(cls, v):
        return _as_datetime(v)


class TaskUpdate(BaseModel):
    title: Optional[constr(min_length=1, max_length=200)] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def _status_any_case_u(cls, v):
        if v is None or isinstance(v, TaskStatus):
            return v
        return TaskStatus(_normalize_enum_value(v))

    @field_validator("priority", mode="before")
    @classmethod
    def _priority_any_case_u(cls, v):
        if v is None or isinstance(v, TaskPriority):
            return v
        return TaskPriority(_normalize_enum_value(v))

    @field_validator("due_date", mode="before")
    @classmethod
    def _due_any_format_u(cls, v):
        return _as_datetime(v)


class TaskResponse(TaskBase):
    id: int
    owner_id: int
    category_id: Optional[int] = None
    due_date: Optional[datetime] = None

    class Config:
        from_attributes = True
