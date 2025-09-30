from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from .base import BaseModel
from datetime import datetime
import enum


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ARCHIVED = "archived"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


def _normalize_status(value) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    import enum as py_enum
    if isinstance(value, py_enum.Enum):
        value = value.value
    if value is None:
        return TaskStatus.TODO
    s = str(value).strip().lower().replace("-", "_")
    aliases = {"inprogress": "in_progress", "in progress": "in_progress"}
    s = aliases.get(s, s)
    return TaskStatus(s)


def _normalize_priority(value) -> TaskPriority:
    if isinstance(value, TaskPriority):
        return value
    import enum as py_enum
    if isinstance(value, py_enum.Enum):
        value = value.value
    if value is None:
        return TaskPriority.MEDIUM
    s = str(value).strip().lower()
    return TaskPriority(s)


class Task(BaseModel):
    __tablename__ = "tasks"

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(
        PGEnum(
            TaskStatus,
            name="taskstatus",
            create_type=False,
            validate_strings=True,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
        server_default=text("'todo'::taskstatus"),
    )

    priority = Column(
        PGEnum(
            TaskPriority,
            name="taskpriority",
            create_type=False,
            validate_strings=True,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
        server_default=text("'medium'::taskpriority"),
    )

    due_date = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    owner = relationship("User", back_populates="tasks")
    category = relationship("Category", back_populates="tasks")

    @validates("status")
    def _validate_status(self, _, value):
        return _normalize_status(value)

    @validates("priority")
    def _validate_priority(self, _, value):
        return _normalize_priority(value)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_overdue(self) -> bool:
        if not self.due_date or self.status in [TaskStatus.DONE, TaskStatus.ARCHIVED]:
            return False
        return datetime.utcnow() > self.due_date

    def soft_delete(self) -> None:
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        self.deleted_at = None

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}', owner_id={self.owner_id})>"
