import pytest
from fastapi import status
from app.db.models.category import Category
from tests.conftest import assert_error_response


# -----------------------
# Category Tests
# -----------------------
def test_list_categories(client, auth_headers, test_category):
    response = client.get("/api/v1/categories/", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert any(c["id"] == test_category.id for c in data)


def test_create_category(client, auth_headers, db_session):
    payload = {
        "name": "Work",
        "description": "Work-related tasks",
        "color": "#00FF00"
    }

    response = client.post("/api/v1/categories/", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["name"] == payload["name"]
    assert data["color"] == payload["color"]

    category_in_db = db_session.query(Category).filter_by(name="Work").first()
    assert category_in_db is not None


def test_get_category(client, auth_headers, test_category):
    response = client.get(f"/api/v1/categories/{test_category.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == test_category.id
    assert data["name"] == test_category.name


def test_get_category_not_found(client, auth_headers):
    response = client.get("/api/v1/categories/999999", headers=auth_headers)
    assert_error_response(
        response,
        expected_status=status.HTTP_404_NOT_FOUND,
        expected_message="Category not found"
    )


def test_update_category(client, auth_headers, test_category):
    payload = {"name": "Updated Category", "description": "Updated description"}

    response = client.put(
        f"/api/v1/categories/{test_category.id}",
        json=payload,
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]


def test_delete_category(client, auth_headers, test_category, db_session):
    response = client.delete(f"/api/v1/categories/{test_category.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["message"] == "Category deleted successfully"
    assert data["data"]["category_id"] == test_category.id

    deleted = db_session.query(Category).filter_by(id=test_category.id).first()
    assert deleted is None


def test_get_category_tasks(client, auth_headers, test_category, test_task):
    response = client.get(f"/api/v1/categories/{test_category.id}/tasks", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert any(t["id"] == test_task.id for t in data)

# -----------------------
# Validation Tests (422)
# -----------------------
def test_create_category_missing_name(client, auth_headers):
    payload = {
        # "name" пропущено
        "description": "Description only",
        "color": "#FF0000"
    }

    response = client.post("/api/v1/categories/", json=payload, headers=auth_headers)
    assert_error_response(
        response,
        expected_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_message="Validation error",
        expected_type="validation_error"
    )


def test_create_category_invalid_color(client, auth_headers):
    payload = {
        "name": "InvalidColor",
        "description": "Description",
        "color": "not-a-color"  # Некорректный формат
    }

    response = client.post("/api/v1/categories/", json=payload, headers=auth_headers)
    assert_error_response(
        response,
        expected_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_message="Validation error",
        expected_type="validation_error"
    )


def test_update_category_empty_name(client, auth_headers, test_category):
    payload = {
        "name": "",  # Пустое имя
        "description": "Updated description"
    }

    response = client.put(f"/api/v1/categories/{test_category.id}", json=payload, headers=auth_headers)
    assert_error_response(
        response,
        expected_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_message="Validation error",
        expected_type="validation_error"
    )

