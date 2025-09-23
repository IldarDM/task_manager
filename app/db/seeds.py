from sqlalchemy.orm import Session
from app.db.models.category import Category


def create_default_category_for_user(db: Session, user_id: int) -> Category:
    """Create default 'Uncategorized' category for a user."""
    default_category = Category(
        name="Uncategorized",
        description="Default category for tasks without a specific category",
        color="#6B7280",
        owner_id=user_id,
    )
    db.add(default_category)
    db.commit()
    db.refresh(default_category)
    return default_category


def get_or_create_default_category(db: Session, user_id: int) -> Category:
    """Get the default category or create it if it doesn't exist."""
    category = (
        db.query(Category)
        .filter(Category.owner_id == user_id, Category.name == "Uncategorized")
        .first()
    )
    if not category:
        category = create_default_category_for_user(db, user_id)
    return category
