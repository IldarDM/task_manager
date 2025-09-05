from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.security import verify_token
from app.db.session import get_db
from app.core.redis_client import RedisClient
from app.db.models.user import User

# Security scheme
security = HTTPBearer()


def get_current_user(
        db: Session = Depends(get_db),
        credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify token
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.email == token_data).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user


def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (alias for clarity)."""
    return current_user

def get_redis() -> RedisClient:
    return RedisClient()