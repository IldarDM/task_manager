from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.core.middleware import rate_limit_general
from app.core.exceptions import NotFoundError, ConflictError
from app.db.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.db.schemas.task import TaskResponse
from app.db.schemas.error import SuccessResponse
from app.services.category_service import CategoryService
from app.db.models.user import User
from fastapi import Request
from typing import Any, List

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "/",
    response_model=List[CategoryResponse],
    summary="List user categories",
    description="Get all categories for the current user"
)
async def list_categories(
        *,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        skip: int = Query(0, ge=0, description="Number of categories to skip"),
        limit: int = Query(100, ge=1, le=100, description="Maximum number of categories to return"),
) -> Any:
    """List user categories with pagination."""
    rate_limit_general(request)

    categories = CategoryService.get_user_categories(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

    return categories


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    description="Create a new category for the current user"
)
async def create_category(
        *,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        category_in: CategoryCreate,
) -> Any:
    """Create new category."""
    rate_limit_general(request)

    category = CategoryService.create_category(
        db=db,
        category_create=category_in,
        user_id=current_user.id
    )

    return category


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get category",
    description="Get a specific category by ID"
)
async def get_category(
        *,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        category_id: int,
) -> Any:
    """Get category by ID."""
    rate_limit_general(request)

    category = CategoryService.get_category_by_id(
        db=db,
        category_id=category_id,
        user_id=current_user.id
    )

    if not category:
        raise NotFoundError(detail="Category not found")

    return category


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update category",
    description="Update a specific category"
)
async def update_category(
        *,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        category_id: int,
        category_update: CategoryUpdate,
) -> Any:
    """Update category."""
    rate_limit_general(request)

    category = CategoryService.update_category(
        db=db,
        category_id=category_id,
        category_update=category_update,
        user_id=current_user.id
    )

    return category


@router.delete(
    "/{category_id}",
    response_model=SuccessResponse,
    summary="Delete category",
    description="Delete a category and move its tasks to Uncategorized"
)
async def delete_category(
        *,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        category_id: int,
) -> Any:
    """Delete category."""
    rate_limit_general(request)

    CategoryService.delete_category(
        db=db,
        category_id=category_id,
        user_id=current_user.id
    )

    return SuccessResponse(
        message="Category deleted successfully",
        data={"category_id": category_id}
    )


@router.get(
    "/{category_id}/tasks",
    response_model=List[TaskResponse],
    summary="Get category tasks",
    description="Get all tasks in a specific category"
)
async def get_category_tasks(
        *,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        category_id: int,
        skip: int = Query(0, ge=0, description="Number of tasks to skip"),
        limit: int = Query(100, ge=1, le=100, description="Maximum number of tasks to return"),
        include_deleted: bool = Query(False, description="Include deleted tasks"),
) -> Any:
    """Get tasks for a specific category."""
    rate_limit_general(request)

    tasks = CategoryService.get_category_tasks(
        db=db,
        category_id=category_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted
    )

    return tasks