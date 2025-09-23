from datetime import datetime, timedelta
from typing import Any, Union, Optional, Tuple, List

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str) -> Optional[str]:
    """Verify JWT token and return the subject, or None if invalid or blacklisted."""
    try:
        from app.services.token_service import TokenService

        if TokenService.is_token_blacklisted(token):
            return None

        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("sub")
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """Validate password strength. Returns (is_valid, errors)."""
    errors: List[str] = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    if not any(c in "!@#$%^&*(),.?\":{}|<>" for c in password):
        errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors
