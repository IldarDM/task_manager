from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_
from app.db.models.category import Category
from app.db.models.task import Task
from app.db.schemas.category import CategoryCreate, CategoryUpdate
from app.core.exceptions import NotFoundError, ConflictError
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class CategoryService:
    @staticmethod
    def get_user_categories(
            db: Session,
            user_id: int,
            skip: int = 0,
            limit: int = 100
    ) -> List[Category]:
        """Get all categories for a user with pagination."""
        return (
            db.query(Category)
            .filter(Category.owner_id == user_id)
            .options(selectinload(Category.tasks))  # Eager load tasks for task_count
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_category_by_id(
            db: Session,
            category_id: int,
            user_id: int
    ) -> Optional[Category]:
        """Get category by ID, ensuring user ownership."""
        return (
            db.query(Category)
            .filter(
                and_(
                    Category.id == category_id,
                    Category.owner_id == user_id
                )
            )
            .options(selectinload(Category.tasks))
            .first()
        )

    @staticmethod
    def create_category(
            db: Session,
            category_create: CategoryCreate,
            user_id: int
    ) -> Category:
        """Create new category for user."""
        # Check for duplicate name (case insensitive)
        existing = (
            db.query(Category)
            .filter(
                and_(
                    Category.owner_id == user_id,
                    Category.name.ilike(category_create.name)
                )
            )
            .first()
        )

        if existing:
            raise ConflictError(detail=f"Category '{category_create.name}' already exists")

        # Create category
        db_category = Category(
            **category_create.model_dump(),
            owner_id=user_id
        )

        db.add(db_category)
        db.commit()
        db.refresh(db_category)

        logger.info(f"Created category '{db_category.name}' for user {user_id}")
        return db_category

    @staticmethod
    def update_category(
            db: Session,
            category_id: int,
            category_update: CategoryUpdate,
            user_id: int
    ) -> Category:
        """Update category."""
        # Get category
        category = CategoryService.get_category_by_id(db, category_id, user_id)
        if not category:
            raise NotFoundError(detail="Category not found")

        # Check for duplicate name if name is being updated
        update_data = category_update.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != category.name:
            existing = (
                db.query(Category)
                .filter(
                    and_(
                        Category.owner_id == user_id,
                        Category.name.ilike(update_data["name"]),
                        Category.id != category_id
                    )
                )
                .first()
            )

            if existing:
                raise ConflictError(detail=f"Category '{update_data['name']}' already exists")

        # Update fields
        for field, value in update_data.items():
            setattr(category, field, value)

        db.commit()
        db.refresh(category)

        logger.info(f"Updated category {category_id} for user {user_id}")
        return category

    @staticmethod
    def delete_category(
            db: Session,
            category_id: int,
            user_id: int
    ) -> bool:
        """Delete category and handle associated tasks."""
        category = CategoryService.get_category_by_id(db, category_id, user_id)
        if not category:
            raise NotFoundError(detail="Category not found")

        # Prevent deletion of "Uncategorized" category
        if category.name == "Uncategorized":
            raise ConflictError(detail="Cannot delete the 'Uncategorized' category")

        # Get or create "Uncategorized" category
        uncategorized = CategoryService.get_or_create_uncategorized(db, user_id)

        # Move tasks to "Uncategorized"
        task_count = (
            db.query(Task)
            .filter(
                and_(
                    Task.category_id == category_id,
                    Task.deleted_at.is_(None)  # Only non-deleted tasks
                )
            )
            .update({Task.category_id: uncategorized.id})
        )

        # Delete category
        db.delete(category)
        db.commit()

        logger.info(f"Deleted category {category_id}, moved {task_count} tasks to Uncategorized")
        return True

    @staticmethod
    def get_or_create_uncategorized(db: Session, user_id: int) -> Category:
        """Get or create the 'Uncategorized' category for a user."""
        uncategorized = (
            db.query(Category)
            .filter(
                and_(
                    Category.owner_id == user_id,
                    Category.name == "Uncategorized"
                )
            )
            .first()
        )

        if not uncategorized:
            from app.db.seeds import create_default_category_for_user
            uncategorized = create_default_category_for_user(db, user_id)

        return uncategorized

    @staticmethod
    def get_category_tasks(
            db: Session,
            category_id: int,
            user_id: int,
            skip: int = 0,
            limit: int = 100,
            include_deleted: bool = False
    ):
        """Get tasks for a specific category."""
        # Verify category ownership
        category = CategoryService.get_category_by_id(db, category_id, user_id)
        if not category:
            raise NotFoundError(detail="Category not found")

        query = db.query(Task).filter(Task.category_id == category_id)

        if not include_deleted:
            query = query.filter(Task.deleted_at.is_(None))

        return query.offset(skip).limit(limit).all()