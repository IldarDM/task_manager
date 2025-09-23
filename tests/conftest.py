import os

import pytest
import asyncio
from typing import Generator, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from faker import Faker

from app.core.redis_client import RedisClient
from app.main import app
from app.core.deps import get_db, get_redis
from app.db.models.base import Base
from app.db.models.user import User
from app.db.models.category import Category
from app.db.models.task import Task, TaskStatus, TaskPriority
from app.core.security import get_password_hash
from app.services.auth_service import AuthService

os.environ["ENV_FILE"] = ".env.test"

from app.core.config import settings

def assert_error_response(response, expected_status: int, expected_message: str, expected_type: str = "http_error"):
    """Проверка кастомного формата ошибки."""
    assert response.status_code == expected_status

    data = response.json()
    assert data["error"] is True
    assert data["message"] == expected_message
    assert any(d["type"] == expected_type for d in data["details"])



# Create test database engine
test_engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)

fake = Faker()


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create database session for tests."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def redis_client():
    client = RedisClient()
    client.redis_client.flushdb()
    yield client
    client.redis_client.flushdb()

@pytest.fixture
def client(db_session, redis_client):
    def override_get_db():
        yield db_session

    def override_get_redis():
        return redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()



# User Fixtures
@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        email=fake.email(),
        hashed_password=get_password_hash("TestPassword123!"),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create default "Uncategorized" category
    from app.db.seeds import create_default_category_for_user
    create_default_category_for_user(db_session, user.id)

    return user


@pytest.fixture
def another_user(db_session: Session) -> User:
    """Create another test user for isolation tests."""
    user = User(
        email=fake.email(),
        hashed_password=get_password_hash("TestPassword123!"),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create default "Uncategorized" category
    from app.db.seeds import create_default_category_for_user
    create_default_category_for_user(db_session, user.id)

    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Create authentication headers for test user."""
    token = AuthService.create_access_token_for_user(test_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_category(db_session: Session, test_user: User) -> Category:
    """Create a test category."""
    category = Category(
        name=fake.word().title(),
        description=fake.text(max_nb_chars=100),
        color="#FF6B35",
        owner_id=test_user.id
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def test_task(db_session: Session, test_user: User, test_category: Category) -> Task:
    """Create a test task using TaskService to ensure Pydantic serialization works."""
    from app.services.task_service import TaskService
    from app.db.schemas.task import TaskCreate

    task_data = TaskCreate(
        title="Use actually.",
        description="Test description",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        category_id=test_category.id
    )
    task = TaskService.create_task(db_session, task_data, test_user.id)
    return task



# Factory fixtures for creating multiple items
@pytest.fixture
def user_factory(db_session: Session):
    """Factory for creating multiple users."""
    created_users = []

    def _create_user(**kwargs) -> User:
        defaults = {
            "email": fake.email(),
            "hashed_password": get_password_hash("TestPassword123!"),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
        }
        defaults.update(kwargs)

        user = User(**defaults)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        created_users.append(user)
        return user

    yield _create_user

    # Cleanup
    for user in created_users:
        db_session.delete(user)
    db_session.commit()


@pytest.fixture
def category_factory(db_session: Session):
    """Factory for creating multiple categories."""
    created_categories = []

    def _create_category(user_id: int, **kwargs) -> Category:
        defaults = {
            "name": fake.word().title(),
            "description": fake.text(max_nb_chars=100),
            "color": fake.color(),
            "owner_id": user_id
        }
        defaults.update(kwargs)

        category = Category(**defaults)
        db_session.add(category)
        db_session.commit()
        db_session.refresh(category)

        created_categories.append(category)
        return category

    yield _create_category

    # Cleanup
    for category in created_categories:
        db_session.delete(category)
    db_session.commit()


@pytest.fixture
def task_factory(db_session: Session):
    """Factory for creating multiple tasks."""
    created_tasks = []

    def _create_task(user_id: int, category_id: int, **kwargs) -> Task:
        defaults = {
            "title": fake.sentence(nb_words=3),
            "description": fake.text(max_nb_chars=200),
            "status": TaskStatus.TODO,
            "priority": TaskPriority.MEDIUM,
            "owner_id": user_id,
            "category_id": category_id
        }
        defaults.update(kwargs)

        task = Task(**defaults)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        created_tasks.append(task)
        return task

    yield _create_task

    # Cleanup
    for task in created_tasks:
        db_session.delete(task)
    db_session.commit()