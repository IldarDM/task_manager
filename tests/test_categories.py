import pytest
from fastapi import status
from typing import Dict
from app.db.models.category import Category
from tests.conftest import assert_error_response


# -----------------------
# Helpers
# -----------------------
def assert_category_in_db(db_session, name: str) -> Category:
    category = db_session.query(Category).filter_by(name=name).first()
    assert category is not None
    return category


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
    payload: Dict[str, str] = {
        "name": "Work",
        "description": "Work-related tasks",
        "color": "#00FF00"
    }

    response = client.post("/api/v1/categories/", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["name"] == payload["name"]
    assert data["color"] == payload["color"]

    assert_category_in_db(db_session, payload["name"])


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
    payload: Dict[str, str] = {
        "name": "Updated Category",
        "description": "Updated description"
    }

    response = client.put(f"/api/v1/categories/{test_category.id}", json=payload, headers=auth_headers)
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
@pytest.mark.parametrize(
    "payload, expected_type",
    [
        ({"description": "Description only", "color": "#FF0000"}, "validation_error"),  # missing name
        ({"name": "InvalidColor", "description": "Description", "color": "not-a-color"}, "validation_error"),
        ({"name": "", "description": "Updated description"}, "validation_error"),
    ]
)
def test_category_validation(client, auth_headers, test_category, payload, expected_type):
    # Determine endpoint and method
    category_id = getattr(test_category, "id", 1)
    if "name" in payload and payload["name"] == "":
        # Update empty name
        response = client.put(f"/api/v1/categories/{category_id}", json=payload, headers=auth_headers)
    else:
        response = client.post("/api/v1/categories/", json=payload, headers=auth_headers)

    assert_error_response(
        response,
        expected_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_message="Validation error",
        expected_type=expected_type
    )
