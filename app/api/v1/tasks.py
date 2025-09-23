from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.middleware import rate_limit_general
from app.core.exceptions import NotFoundError
from app.db.models.user import User
from app.db.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.db.schemas.error import SuccessResponse
from app.services.task_service import (
    TaskService,
    TaskFilterParams,
    TaskSortParams,
    TaskStatus,
    TaskPriority,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/", response_model=Dict[str, Any])
async def list_tasks(
    *,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[List[TaskStatus]] = Query(None),
    priority: Optional[List[TaskPriority]] = Query(None),
    category_id: Optional[int] = Query(None),
    due_date_from: Optional[datetime] = Query(None),
    due_date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    is_overdue: Optional[bool] = Query(None),
    include_deleted: bool = Query(False),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
) -> Any:
    """List tasks with filters, sorting, and pagination."""
    rate_limit_general(request)
    filters = TaskFilterParams(status, priority, category_id, due_date_from, due_date_to, search, is_overdue)
    sort_params = TaskSortParams(sort_by, sort_order)
    return TaskService.get_user_tasks(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        filters=filters,
        sort_params=sort_params,
        include_deleted=include_deleted,
    )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    *,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_in: TaskCreate,
):
    """Create a new task."""
    rate_limit_general(request)
    return TaskService.create_task(db=db, task_create=task_in, user_id=current_user.id)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    *,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_id: int,
    include_deleted: bool = Query(False),
):
    """Get task by ID."""
    rate_limit_general(request)
    task = TaskService.get_task_by_id(db, task_id, current_user.id, include_deleted=include_deleted)
    if not task:
        raise NotFoundError("Task not found")
    return TaskResponse.from_orm(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    *,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_id: int,
    task_update: TaskUpdate,
):
    """Update task."""
    rate_limit_general(request)
    return TaskService.update_task(db, task_id, task_update, current_user.id)


@router.delete("/{task_id}", response_model=SuccessResponse)
async def delete_task(
    *,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_id: int,
):
    """Soft-delete task."""
    rate_limit_general(request)
    TaskService.soft_delete_task(db, task_id, current_user.id)
    return SuccessResponse(message="Task deleted successfully", data={"task_id": task_id})


@router.post("/{task_id}/restore", response_model=TaskResponse)
async def restore_task(
    *,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_id: int,
):
    """Restore a soft-deleted task."""
    rate_limit_general(request)
    return TaskService.restore_task(db, task_id, current_user.id)


@router.post("/{task_id}/archive", response_model=TaskResponse)
async def archive_task(
    *,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    task_id: int,
):
    """Archive a task."""
    rate_limit_general(request)
    return TaskService.archive_task(db, task_id, current_user.id)


@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_task_stats(
    *,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get task statistics overview for current user."""
    rate_limit_general(request)
    return TaskService.get_task_stats(db, current_user.id)
