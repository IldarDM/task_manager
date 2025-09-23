from fastapi import status
from typing import Dict
from app.db.models.user import User
from tests.conftest import assert_error_response


# -----------------------
# Helpers
# -----------------------
def assert_user_in_db(db_session, email: str):
    user = db_session.query(User).filter_by(email=email).first()
    assert user is not None
    return user


# -----------------------
# Registration Tests
# -----------------------
def test_register_user(client, db_session):
    payload: Dict[str, str] = {
        "email": "newuser@example.com",
        "password": "StrongPass123!",
        "first_name": "John",
        "last_name": "Doe"
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["email"] == payload["email"]
    assert "id" in data

    # Проверка, что пользователь создан в БД
    assert_user_in_db(db_session, payload["email"])


def test_register_user_conflict(client, test_user):
    payload = {
        "email": test_user.email,
        "password": "AnotherPass123!",
        "first_name": "Jane",
        "last_name": "Doe"
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert_error_response(
        response,
        expected_status=status.HTTP_409_CONFLICT,
        expected_message="User with this email already exists"
    )


# -----------------------
# Login Tests
# -----------------------
def test_login_user(client, test_user):
    payload = {"email": test_user.email, "password": "TestPassword123!"}
    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_user_wrong_password(client, test_user):
    payload = {"email": test_user.email, "password": "WrongPassword!"}
    response = client.post("/api/v1/auth/login", json=payload)

    assert_error_response(
        response,
        expected_status=status.HTTP_401_UNAUTHORIZED,
        expected_message="Incorrect email or password"
    )


# -----------------------
# Current User Tests
# -----------------------
def test_get_current_user(client, auth_headers, test_user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["email"] == test_user.email
    assert data["first_name"] == test_user.first_name
    assert data["last_name"] == test_user.last_name


def test_update_current_user(client, auth_headers, test_user):
    payload = {"first_name": "UpdatedName", "last_name": "UpdatedLast"}
    response = client.put("/api/v1/auth/me", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["first_name"] == payload["first_name"]
    assert data["last_name"] == payload["last_name"]
