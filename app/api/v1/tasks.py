from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.middleware import rate_limit_general
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
        raise HTTPException(status_code=400, detail=f"Invalid sort_by. Allowed: {sorted(ALLOWED_SORT_FIELDS)}")

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
