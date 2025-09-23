from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from typing import Optional
from datetime import datetime


class UserService:
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create(db: Session, user_create: UserCreate) -> User:
        """Create new user."""
        # Check if user already exists
        if UserService.get_by_email(db, user_create.email):
            raise ValueError("User with this email already exists")

        # Create user with hashed password
        db_user = User(
            email=user_create.email,
            hashed_password=get_password_hash(user_create.password),
            first_name=user_create.first_name,
            last_name=user_create.last_name,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Create default category for user
        from app.db.seeds import create_default_category_for_user
        create_default_category_for_user(db, db_user.id)

        return db_user

    @staticmethod
    def update(db: Session, user: User, user_update: UserUpdate) -> User:
        """Update user information."""
        update_data = user_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = UserService.get_by_email(db, email)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()

        return user

    @staticmethod
    def reset_password(db: Session, email: str, new_password: str) -> bool:
        """Reset user password (simplified version)."""
        user = UserService.get_by_email(db, email)
        if not user:
            return False

        user.hashed_password = get_password_hash(new_password)
        db.commit()
        return True