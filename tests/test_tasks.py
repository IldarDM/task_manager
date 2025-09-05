import pytest
from fastapi.testclient import TestClient
from app.db.models.task import TaskStatus, TaskPriority
from app.db.models.task import Task
from app.db.models.category import Category
from app.db.models.user import User

# -----------------------
# LIST TASKS
# -----------------------
def test_list_tasks(client: TestClient, auth_headers, test_task):
    response = client.get("/api/v1/tasks/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    # Проверяем ключи
    assert "tasks" in data
    assert len(data["tasks"]) >= 1
    task_item = data["tasks"][0]
    assert "id" in task_item
    assert "title" in task_item
    assert task_item["title"] == test_task.title

    # Проверяем верхнеуровневые поля пагинации
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert "has_more" in data

# -----------------------
# CREATE TASK
# -----------------------
def test_create_task(client: TestClient, auth_headers, test_user, test_category):
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

    assert data["title"] == "New Task"
    assert data["priority"] == "high"  # lower-case
    assert data["status"] == "todo"    # lower-case

# -----------------------
# UPDATE TASK
# -----------------------
def test_update_task(client: TestClient, auth_headers, test_task):
    update_data = {
        "title": "Updated Task",
        "description": "Updated description",
        "status": TaskStatus.DONE
    }
    response = client.put(f"/api/v1/tasks/{test_task.id}", headers=auth_headers, json=update_data)
    assert response.status_code == 200
    data = response.json()

    assert data["title"] == "Updated Task"
    assert data["status"] == "done"  # lower-case

# -----------------------
# ARCHIVE TASK
# -----------------------
def test_archive_task(client: TestClient, auth_headers, test_task, db_session):
    db_task = db_session.query(Task).get(test_task.id)
    db_task.status = TaskStatus.DONE
    db_session.commit()

    response = client.post(f"/api/v1/tasks/{test_task.id}/archive", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "archived"

# -----------------------
# SOFT DELETE AND RESTORE TASK
# -----------------------
def test_soft_delete_and_restore_task(client: TestClient, auth_headers, test_task, db_session):
    # Soft delete
    response = client.delete(f"/api/v1/tasks/{test_task.id}", headers=auth_headers)
    assert response.status_code == 200

    # Проверим, что задача не видна
    response = client.get(f"/api/v1/tasks/{test_task.id}", headers=auth_headers)
    assert response.status_code == 404

    # Restore
    response = client.post(f"/api/v1/tasks/{test_task.id}/restore", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_task.id
    assert data["title"] == test_task.title
