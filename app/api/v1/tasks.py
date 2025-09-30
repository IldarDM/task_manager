from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.middleware import rate_limit_general
from app.core.exceptions import NotFoundError, ConflictError
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

ALLOWED_SORT_FIELDS = {"created_at", "updated_at", "due_date", "priority", "status", "title"}


# ---------- LIST + FILTERS ----------
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
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
) -> Any:
    rate_limit_general(request)

    if sort_by not in ALLOWED_SORT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by. Allowed: {sorted(ALLOWED_SORT_FIELDS)}",
        )

    filters = TaskFilterParams(
        status=status,
        priority=priority,
        category_id=category_id,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        search=search,
        is_overdue=is_overdue,
    )
    sort_params = TaskSortParams(sort_by=sort_by, sort_order=sort_order)

    return TaskService.get_user_tasks(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        filters=filters,
        sort_params=sort_params,
        include_deleted=include_deleted,
    )


# ---------- STATS ----------
@router.get("/stats", response_model=Dict[str, Any])
async def get_stats(
    *,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    rate_limit_general(request)
    return TaskService.get_task_stats(db=db, user_id=current_user.id)


# ---------- GET BY ID ----------
@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    *,
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    rate_limit_general(request)
    task = TaskService.get_task_by_id(db=db, task_id=task_id, user_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.from_orm(task)


# ---------- CREATE ----------
@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    *,
    request: Request,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    rate_limit_general(request)
    return TaskService.create_task(db=db, task_create=payload, user_id=current_user.id)


# ---------- UPDATE (partial) ----------
@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    *,
    request: Request,
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    rate_limit_general(request)
    try:
        return TaskService.update_task(db=db, task_id=task_id, task_update=payload, user_id=current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail)


# ---------- SOFT DELETE ----------
@router.delete("/{task_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def delete_task(
    *,
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    rate_limit_general(request)
    try:
        TaskService.soft_delete_task(db=db, task_id=task_id, user_id=current_user.id)
        return SuccessResponse(success=True, message="Task soft-deleted")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail)


# ---------- RESTORE ----------
@router.post("/{task_id}/restore", response_model=TaskResponse)
async def restore_task(
    *,
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    rate_limit_general(request)
    try:
        return TaskService.restore_task(db=db, task_id=task_id, user_id=current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail)


# ---------- ARCHIVE (only DONE) ----------
@router.post("/{task_id}/archive", response_model=TaskResponse)
async def archive_task(
    *,
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    rate_limit_general(request)
    try:
        return TaskService.archive_task(db=db, task_id=task_id, user_id=current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=e.detail)
