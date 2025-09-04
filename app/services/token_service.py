from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from app.core.config import settings
from app.core.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)


class TokenService:
    @staticmethod
    def blacklist_token(token: str) -> bool:
        """Add token to blacklist."""
        try:
            # Decode token to get expiration
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            exp = payload.get("exp")
            if not exp:
                return False

            # Calculate TTL (time until expiration)
            current_time = datetime.utcnow().timestamp()
            ttl = int(exp - current_time)

            if ttl > 0:
                # Store in Redis with TTL
                key = f"blacklisted_token:{token}"
                return redis_client.set(key, "true", ex=ttl)

            return True  # Token already expired

        except JWTError as e:
            logger.error(f"Error blacklisting token: {e}")
            return False

    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        """Check if token is blacklisted."""
        try:
            key = f"blacklisted_token:{token}"
            return redis_client.exists(key)
        except Exception as e:
            logger.error(f"Error checking token blacklist: {e}")
            # If Redis is down, assume token is not blacklisted for availability
            return False