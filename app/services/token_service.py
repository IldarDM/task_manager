from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from app.core.config import settings
from app.core.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)

REFRESH_PREFIX = "refresh_token:"
BLACKLIST_PREFIX = "blacklisted_token:"

class TokenService:
    # ===== Access blacklist =====
    @staticmethod
    def blacklist_token(token: str) -> bool:
        """Add access token to blacklist until its exp."""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            exp = payload.get("exp")
            if not exp:
                return False
            ttl = max(0, int(exp - datetime.utcnow().timestamp()))
            if ttl > 0:
                return redis_client.set(f"{BLACKLIST_PREFIX}{token}", "true", ex=ttl)
            return True
        except JWTError as e:
            logger.error(f"Error blacklisting token: {e}")
            return False

    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        try:
            return redis_client.exists(f"{BLACKLIST_PREFIX}{token}")
        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
            return False

    # ===== Refresh storage & rotation =====
    @staticmethod
    def store_refresh_token(token: str, email: str) -> bool:
        """Store refresh token with TTL; value = email. Used for rotation/validation."""
        ttl = settings.refresh_token_expire_days * 86400
        return redis_client.set(f"{REFRESH_PREFIX}{token}", email, ex=ttl)

    @staticmethod
    def get_refresh_owner(token: str) -> Optional[str]:
        return redis_client.get(f"{REFRESH_PREFIX}{token}")

    @staticmethod
    def revoke_refresh_token(token: str) -> bool:
        return redis_client.delete(f"{REFRESH_PREFIX}{token}")

    @staticmethod
    def revoke_all_user_refresh(email: str) -> None:
        """(Опционально) реализовать pattern-scan по ключам"""
        pass
