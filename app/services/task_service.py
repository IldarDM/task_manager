from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, asc
from app.db.models.task import Task, TaskStatus, TaskPriority
from app.db.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.core.exceptions import NotFoundError, ConflictError
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
import enum as py_enum

logger = logging.getLogger(__name__)


class TaskFilterParams:
    def __init__(
        self,
        status: Optional[List[TaskStatus]] = None,
        priority: Optional[List[TaskPriority]] = None,
        category_id: Optional[int] = None,
        due_date_from: Optional[datetime] = None,
        due_date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        is_overdue: Optional[bool] = None,
    ):
        self.status = status or []
        self.priority = priority or []
        self.category_id = category_id
        self.due_date_from = due_date_from
        self.due_date_to = due_date_to
        self.search = search
        self.is_overdue = is_overdue


class TaskSortParams:
    def __init__(self, sort_by: str = "created_at", sort_order: str = "desc"):
        self.sort_by = sort_by
        self.sort_order = sort_order


def _normalize_status(value) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    if isinstance(value, py_enum.Enum):
        value = value.value
    if value is None:
        return TaskStatus.TODO
    s = str(value).strip().lower().replace("-", "_")
    aliases = {"inprogress": "in_progress", "in progress": "in_progress"}
    s = aliases.get(s, s)
    return TaskStatus(s)


def _normalize_priority(value) -> TaskPriority:
    if isinstance(value, TaskPriority):
        return value
    if isinstance(value, py_enum.Enum):
        value = value.value
    if value is None:
        return TaskPriority.MEDIUM
    s = str(value).strip().lower()
    return TaskPriority(s)


class TaskService:
    @staticmethod
    def get_user_tasks(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        filters: Optional[TaskFilterParams] = None,
        sort_params: Optional[TaskSortParams] = None,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        query = (
            db.query(Task)
            .filter(Task.owner_id == user_id)
            .options(selectinload(Task.category))
        )

        if not include_deleted:
            query = query.filter(Task.deleted_at.is_(None))

        if filters:
            query = TaskService._apply_filters(query, filters)

        if sort_params:
            query = TaskService._apply_sorting(query, sort_params)
        else:
            query = query.order_by(desc(Task.created_at))

        total = query.count()
        tasks = query.offset(skip).limit(limit).all()
        tasks_response = [TaskResponse.from_orm(task) for task in tasks]

        return {
            "tasks": tasks_response,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + len(tasks) < total,
        }

    @staticmethod
    def _apply_filters(query, filters: TaskFilterParams):
        if filters.status:
            query = query.filter(Task.status.in_(filters.status))
        if filters.priority:
            query = query.filter(Task.priority.in_(filters.priority))
        if filters.category_id:
            query = query.filter(Task.category_id == filters.category_id)
        if filters.due_date_from:
            query = query.filter(Task.due_date >= filters.due_date_from)
        if filters.due_date_to:
            query = query.filter(Task.due_date <= filters.due_date_to)
        if filters.search:
            like = f"%{filters.search}%"
            query = query.filter(or_(Task.title.ilike(like), Task.description.ilike(like)))
        if filters.is_overdue is True:
            now = datetime.utcnow()
            query = query.filter(
                and_(
                    Task.due_date.isnot(None),
                    Task.due_date < now,
                    Task.status.notin_([TaskStatus.DONE, TaskStatus.ARCHIVED]),
                )
            )
        if filters.is_overdue is False:
            now = datetime.utcnow()
            query = query.filter(or_(Task.due_date.is_(None), Task.due_date >= now))
        return query

    @staticmethod
    def _apply_sorting(query, sort_params: TaskSortParams):
        mapping = {
            "created_at": Task.created_at,
            "updated_at": Task.updated_at,
            "due_date": Task.due_date,
            "priority": Task.priority,
            "status": Task.status,
            "title": Task.title,
        }
        column = mapping.get(sort_params.sort_by, Task.created_at)
        order_fn = desc if sort_params.sort_order.lower() == "desc" else asc
        return query.order_by(order_fn(column))

    @staticmethod
    def create_task(db: Session, task_create: TaskCreate, user_id: int) -> TaskResponse:
        provided = task_create.model_fields_set

        title = task_create.title
        description = task_create.description
        due_date = getattr(task_create, "due_date", None)
        category_id = getattr(task_create, "category_id", None)

        kwargs = dict(
            title=title,
            description=description,
            due_date=due_date,
            category_id=category_id,
            owner_id=user_id,
        )

        if "status" in provided:
            kwargs["status"] = _normalize_status(getattr(task_create, "status", None))
        if "priority" in provided:
            kwargs["priority"] = _normalize_priority(getattr(task_create, "priority", None))

        db_task = Task(**kwargs)

        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return TaskResponse.from_orm(db_task)

    @staticmethod
    def get_task_by_id(db: Session, task_id: int, user_id: int) -> Optional[Task]:
        return db.query(Task).filter(and_(Task.id == task_id, Task.owner_id == user_id)).first()

    @staticmethod
    def update_task(db: Session, task_id: int, task_update: TaskUpdate, user_id: int) -> TaskResponse:
        task = TaskService.get_task_by_id(db, task_id, user_id)
        if not task:
            raise NotFoundError(detail="Task not found")

        data = task_update.model_dump(exclude_unset=True)

        if "status" in data:
            data["status"] = _normalize_status(data["status"])
        if "priority" in data:
            data["priority"] = _normalize_priority(data["priority"])

        for f, v in data.items():
            setattr(task, f, v)

        db.commit()
        db.refresh(task)
        return TaskResponse.from_orm(task)

    @staticmethod
    def soft_delete_task(db: Session, task_id: int, user_id: int) -> bool:
        task = TaskService.get_task_by_id(db, task_id, user_id)
        if not task:
            raise NotFoundError(detail="Task not found")
        task.deleted_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def restore_task(db: Session, task_id: int, user_id: int) -> TaskResponse:
        task = TaskService.get_task_by_id(db, task_id, user_id)
        if not task:
            raise NotFoundError(detail="Task not found")
        task.deleted_at = None
        db.commit()
        db.refresh(task)
        return TaskResponse.from_orm(task)

    @staticmethod
    def archive_task(db: Session, task_id: int, user_id: int) -> TaskResponse:
        task = TaskService.get_task_by_id(db, task_id, user_id)
        if not task:
            raise NotFoundError(detail="Task not found")
        if task.status != TaskStatus.DONE:
            raise ConflictError(detail="Only completed tasks can be archived")
        task.status = TaskStatus.ARCHIVED
        db.commit()
        db.refresh(task)
        return TaskResponse.from_orm(task)

    @staticmethod
    def get_task_stats(db: Session, user_id: int) -> Dict[str, Any]:
        base = db.query(Task).filter(and_(Task.owner_id == user_id, Task.deleted_at.is_(None)))
        total = base.count()
        status_counts = {s.value: base.filter(Task.status == s).count() for s in TaskStatus}
        priority_counts = {p.value: base.filter(Task.priority == p).count() for p in TaskPriority}
        now = datetime.utcnow()
        overdue = base.filter(
            and_(
                Task.due_date < now,
                Task.status.notin_([TaskStatus.DONE, TaskStatus.ARCHIVED]),
            )
        ).count()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        due_today = base.filter(
            and_(
                Task.due_date >= today_start,
                Task.due_date <= today_end,
                Task.status.notin_([TaskStatus.DONE, TaskStatus.ARCHIVED]),
            )
        ).count()
        return {
            "total_tasks": total,
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "overdue_count": overdue,
            "due_today_count": due_today,
        }
