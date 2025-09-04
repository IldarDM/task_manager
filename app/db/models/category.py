from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class Category(BaseModel):
    __tablename__ = "categories"

    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    color = Column(String(7), default="#6B7280", nullable=False)  # Hex color
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="categories")
    tasks = relationship("Task", back_populates="category", cascade="all, delete-orphan")

    @property
    def task_count(self) -> int:
        """Return count of non-deleted tasks in this category."""
        return len([task for task in self.tasks if task.deleted_at is None])

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"