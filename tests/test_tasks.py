import pytest
from fastapi.testclient import TestClient
from app.db.models.task import TaskStatus, TaskPriority, Task
from app.db.models.category import Category
from app.db.models.user import User


# -----------------------
# Helpers
# -----------------------
def assert_task_keys(task_data: dict):
    keys = ["id", "title", "description", "status", "priority", "category_id", "owner_id", "created_at", "updated_at", "is_overdue"]
    for key in keys:
        assert key in task_data


# -----------------------
# LIST TASKS
# -----------------------
def test_list_tasks(client: TestClient, auth_headers, test_task: Task):
    response = client.get("/api/v1/tasks/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert "tasks" in data
    assert len(data["tasks"]) >= 1
    assert_task_keys(data["tasks"][0])

    task_item = data["tasks"][0]
    assert task_item["title"] == test_task.title

    # Проверяем пагинацию
    for key in ["total", "skip", "limit", "has_more"]:
        assert key in data


# -----------------------
# CREATE TASK
# -----------------------
def test_create_task(client: TestClient, auth_headers, test_user: User, test_category: Category):
    task_data = {
        "title": "New Task",
        "description": "Task description",
        "status": TaskStatus.TODO,
        "priority": TaskPriority.HIGH,
        "category_id": test_category.id
    }
    response = client.post("/api/v1/tasks/", headers=auth_headers, json=task_data)
    assert response.status_code == 201

    data = response.json()
    assert data["title"] == task_data["title"]
    assert data["status"] == task_data["status"].value
    assert data["priority"] == task_data["priority"].value
    assert data["category_id"] == test_category.id
    assert_task_keys(data)


# -----------------------
# UPDATE TASK
# -----------------------
def test_update_task(client: TestClient, auth_headers, test_task: Task):
    update_data = {
        "title": "Updated Task",
        "description": "Updated description",
        "status": TaskStatus.DONE
    }
    response = client.put(f"/api/v1/tasks/{test_task.id}", headers=auth_headers, json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["status"] == update_data["status"].value
    assert_task_keys(data)


# -----------------------
# ARCHIVE TASK
# -----------------------
def test_archive_task(client: TestClient, auth_headers, test_task: Task, db_session):
    # Обновим статус на DONE перед архивированием
    db_task = db_session.get(Task, test_task.id)
    db_task.status = TaskStatus.DONE
    db_session.commit()

    response = client.post(f"/api/v1/tasks/{test_task.id}/archive", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == TaskStatus.ARCHIVED.value
    assert_task_keys(data)


# -----------------------
# SOFT DELETE AND RESTORE TASK
# -----------------------
def test_soft_delete_and_restore_task(client: TestClient, auth_headers, test_task: Task):
    # Soft delete
    response = client.delete(f"/api/v1/tasks/{test_task.id}", headers=auth_headers)
    assert response.status_code == 200

    # Проверим, что задача недоступна
    response = client.get(f"/api/v1/tasks/{test_task.id}", headers=auth_headers)
    assert response.status_code == 404

    # Restore
    response = client.post(f"/api/v1/tasks/{test_task.id}/restore", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == test_task.id
    assert data["title"] == test_task.title
    assert_task_keys(data)
