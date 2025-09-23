import os
from typing import Generator, Any, Callable, List, Dict
from datetime import datetime

import pytest
from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.deps import get_db, get_redis
from app.core.redis_client import RedisClient
from app.core.security import get_password_hash
from app.services.auth_service import AuthService
from app.db.models.base import Base
from app.db.models.user import User
from app.db.models.category import Category
from app.db.models.task import Task, TaskStatus, TaskPriority

os.environ["ENV_FILE"] = ".env.test"
from app.core.config import settings

fake = Faker()

# -----------------------
# Helper Functions
# -----------------------
def assert_error_response(response, expected_status: int, expected_message: str, expected_type: str = "http_error"):
    """Check custom error response format."""
    assert response.status_code == expected_status
    data = response.json()
    assert data["error"] is True
    assert data["message"] == expected_message
    assert any(d["type"] == expected_type for d in (data.get("details") or []))


# -----------------------
# Database Fixtures
# -----------------------
test_engine = create_engine(settings.database_url, echo=False, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def db_engine() -> Generator:
    """Create and drop test database schema."""
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a database session with rollback after test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# -----------------------
# Redis Fixture
# -----------------------
@pytest.fixture
def redis_client() -> Generator[RedisClient, None, None]:
    client = RedisClient()
    client.redis_client.flushdb()
    yield client
    client.redis_client.flushdb()


# -----------------------
# Test Client Fixture
# -----------------------
@pytest.fixture
def client(db_session: Session, redis_client: RedisClient) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: redis_client

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# -----------------------
# User Fixtures
# -----------------------
@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user with default category."""
    user = User(
        email=fake.email(),
        hashed_password=get_password_hash("TestPassword123!"),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create default category
    from app.db.seeds import create_default_category_for_user
    create_default_category_for_user(db_session, user.id)

    return user


@pytest.fixture
def another_user(db_session: Session) -> User:
    """Create another test user for isolation tests."""
    return test_user(db_session)


@pytest.fixture
def auth_headers(test_user: User) -> Dict[str, str]:
    """Create authorization headers for a user."""
    token = AuthService.create_access_token_for_user(test_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_category(db_session: Session, test_user: User) -> Category:
    """Create a single test category."""
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
    """Create a single test task via TaskService for proper serialization."""
    from app.services.task_service import TaskService
    from app.db.schemas.task import TaskCreate

    task_data = TaskCreate(
        title="Use actually.",
        description="Test description",
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        category_id=test_category.id
    )
    return TaskService.create_task(db_session, task_data, test_user.id)


# -----------------------
# Factory Fixtures
# -----------------------
@pytest.fixture
def user_factory(db_session: Session) -> Callable[..., User]:
    created_users: List[User] = []

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
def category_factory(db_session: Session) -> Callable[..., Category]:
    created_categories: List[Category] = []

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

    for category in created_categories:
        db_session.delete(category)
    db_session.commit()


@pytest.fixture
def task_factory(db_session: Session) -> Callable[..., Task]:
    created_tasks: List[Task] = []

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

    for task in created_tasks:
        db_session.delete(task)
    db_session.commit()
