from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from .base import BaseModel
from datetime import datetime


class User(BaseModel):
    """User model representing registered users."""
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    tasks = relationship(
        "Task",
        back_populates="owner",
        cascade="all, delete-orphan"
    )
    categories = relationship(
        "Category",
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        """
        Return the user's full name if available,
        otherwise fall back to first name or the email username.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        return self.email.split("@")[0]

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"
