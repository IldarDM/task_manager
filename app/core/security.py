from datetime import datetime, timedelta
from typing import Any, Union, Optional, Tuple, List

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _create_token(subject: Union[str, Any], expires_delta: timedelta, token_type: str) -> str:
    expire = datetime.utcnow() + expires_delta
    to_encode = {"exp": expire, "sub": str(subject), "type": token_type}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    return _create_token(
        subject,
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes),
        token_type="access",
    )

def create_refresh_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    return _create_token(
        subject,
        expires_delta or timedelta(days=settings.refresh_token_expire_days),
        token_type="refresh",
    )

def _verify_token(token: str, expected_type: Optional[str] = None) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if expected_type and payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None

def verify_access_token(token: str) -> Optional[str]:
    try:
        from app.services.token_service import TokenService
        if TokenService.is_token_blacklisted(token):
            return None
    except Exception:
        pass
    return _verify_token(token, expected_type="access")

def verify_token(token: str) -> Optional[str]:
    return verify_access_token(token)

def verify_refresh_token(token: str) -> Optional[str]:
    return _verify_token(token, expected_type="refresh")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
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
