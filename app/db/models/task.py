from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
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


class Task(BaseModel):
    """Task model representing user tasks."""
    __tablename__ = "tasks"

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    due_date = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete timestamp

    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="tasks")
    category = relationship("Category", back_populates="tasks")

    @property
    def is_deleted(self) -> bool:
        """Return True if task is soft deleted."""
        return self.deleted_at is not None

    @property
    def is_overdue(self) -> bool:
        """Return True if task is overdue."""
        if not self.due_date or self.status in [TaskStatus.DONE, TaskStatus.ARCHIVED]:
            return False
        return datetime.utcnow() > self.due_date

    def soft_delete(self) -> None:
        """Mark task as deleted (soft delete)."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore a soft-deleted task."""
        self.deleted_at = None

    def __repr__(self) -> str:
        return (
            f"<Task(id={self.id}, title='{self.title}', status='{self.status}', "
            f"owner_id={self.owner_id})>"
        )
