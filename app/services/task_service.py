from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, asc
from app.db.models.task import Task, TaskStatus, TaskPriority
from app.db.models.category import Category
from app.db.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.core.exceptions import NotFoundError, ConflictError
from app.services.category_service import CategoryService
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TaskFilterParams:
    """Task filtering parameters."""

    def __init__(
            self,
            status: Optional[List[TaskStatus]] = None,
            priority: Optional[List[TaskPriority]] = None,
            category_id: Optional[int] = None,
            due_date_from: Optional[datetime] = None,
            due_date_to: Optional[datetime] = None,
            search: Optional[str] = None,
            is_overdue: Optional[bool] = None
    ):
        self.status = status or []
        self.priority = priority or []
        self.category_id = category_id
        self.due_date_from = due_date_from
        self.due_date_to = due_date_to
        self.search = search
        self.is_overdue = is_overdue


class TaskSortParams:
    """Task sorting parameters."""

    def __init__(
            self,
            sort_by: str = "created_at",
            sort_order: str = "desc"
    ):
        self.sort_by = sort_by
        self.sort_order = sort_order


class TaskService:
    @staticmethod
    def get_user_tasks(
            db: Session,
            user_id: int,
            skip: int = 0,
            limit: int = 20,
            filters: Optional[TaskFilterParams] = None,
            sort_params: Optional[TaskSortParams] = None,
            include_deleted: bool = False
    ) -> Dict[str, Any]:
        """Get user tasks with filtering, sorting, and pagination."""
        query = (
            db.query(Task)
            .filter(Task.owner_id == user_id)
            .options(selectinload(Task.category))
        )

        # Soft delete
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

        # 🔹 Сериализация в Pydantic
        tasks_response = [TaskResponse.from_orm(task) for task in tasks]

        return {
            "tasks": tasks_response,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + len(tasks) < total
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
            search_term = f"%{filters.search}%"
            query = query.filter(or_(Task.title.ilike(search_term), Task.description.ilike(search_term)))
        if filters.is_overdue is not None:
            current_time = datetime.utcnow()
            if filters.is_overdue:
                query = query.filter(
                    and_(Task.due_date < current_time, Task.status.notin_([TaskStatus.DONE, TaskStatus.ARCHIVED]))
                )
            else:
                query = query.filter(
                    or_(Task.due_date.is_(None), Task.due_date >= current_time, Task.status.in_([TaskStatus.DONE, TaskStatus.ARCHIVED]))
                )
        return query

    @staticmethod
    def _apply_sorting(query, sort_params: TaskSortParams):
        sort_column = getattr(Task, sort_params.sort_by, Task.created_at)
        if sort_params.sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        return query

    @staticmethod
    def get_task_by_id(db: Session, task_id: int, user_id: int, include_deleted: bool = False) -> Optional[Task]:
        query = db.query(Task).filter(and_(Task.id == task_id, Task.owner_id == user_id)).options(selectinload(Task.category))
        if not include_deleted:
            query = query.filter(Task.deleted_at.is_(None))
        return query.first()

    @staticmethod
    def create_task(db: Session, task_create: TaskCreate, user_id: int) -> TaskResponse:
        category_id = task_create.category_id
        if not category_id:
            uncategorized = CategoryService.get_or_create_uncategorized(db, user_id)
            category_id = uncategorized.id
        else:
            category = CategoryService.get_category_by_id(db, category_id, user_id)
            if not category:
                raise NotFoundError(detail="Category not found")

        db_task = Task(**task_create.model_dump(exclude={"category_id"}), category_id=category_id, owner_id=user_id)
        db.add(db_task)
        db.commit()
        db.refresh(db_task)

        return TaskResponse.from_orm(db_task)

    @staticmethod
    def update_task(db: Session, task_id: int, task_update: TaskUpdate, user_id: int) -> TaskResponse:
        task = TaskService.get_task_by_id(db, task_id, user_id)
        if not task:
            raise NotFoundError(detail="Task not found")

        update_data = task_update.model_dump(exclude_unset=True)
        if "category_id" in update_data:
            new_category_id = update_data["category_id"]
            if new_category_id:
                category = CategoryService.get_category_by_id(db, new_category_id, user_id)
                if not category:
                    raise NotFoundError(detail="Category not found")
            else:
                uncategorized = CategoryService.get_or_create_uncategorized(db, user_id)
                update_data["category_id"] = uncategorized.id

        for field, value in update_data.items():
            setattr(task, field, value)

        db.commit()
        db.refresh(task)
        return TaskResponse.from_orm(task)

    @staticmethod
    def soft_delete_task(db: Session, task_id: int, user_id: int) -> bool:
        task = TaskService.get_task_by_id(db, task_id, user_id)
        if not task:
            raise NotFoundError(detail="Task not found")
        task.soft_delete()
        db.commit()
        return True

    @staticmethod
    def restore_task(db: Session, task_id: int, user_id: int) -> TaskResponse:
        task = TaskService.get_task_by_id(db, task_id, user_id, include_deleted=True)
        if not task:
            raise NotFoundError(detail="Task not found")
        if not task.is_deleted:
            raise ConflictError(detail="Task is not deleted")
        task.restore()
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
        base_query = db.query(Task).filter(and_(Task.owner_id == user_id, Task.deleted_at.is_(None)))
        total_tasks = base_query.count()

        status_counts = {status.value: base_query.filter(Task.status == status).count() for status in TaskStatus}
        priority_counts = {priority.value: base_query.filter(Task.priority == priority).count() for priority in TaskPriority}

        current_time = datetime.utcnow()
        overdue_count = base_query.filter(and_(Task.due_date < current_time, Task.status.notin_([TaskStatus.DONE, TaskStatus.ARCHIVED]))).count()

        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = current_time.replace(hour=23, minute=59, second=59, microsecond=999999)
        due_today_count = base_query.filter(and_(Task.due_date >= today_start, Task.due_date <= today_end, Task.status.notin_([TaskStatus.DONE, TaskStatus.ARCHIVED]))).count()

        return {
            "total_tasks": total_tasks,
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "overdue_count": overdue_count,
            "due_today_count": due_today_count
        }
