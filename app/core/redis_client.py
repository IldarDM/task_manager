import logging
from typing import Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper with connection handling and safe operations."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self) -> None:
        """Connect to Redis and test connection."""
        try:
            self.redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        if not self.redis_client:
            return None
        try:
            return self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration."""
        if not self.redis_client:
            return False
        try:
            return self.redis_client.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    def incr(self, key: str) -> Optional[int]:
        """Increment value in Redis."""
        if not self.redis_client:
            return None
        try:
            return self.redis_client.incr(key)
        except Exception as e:
            logger.error(f"Redis INCR error: {e}")
            return None

    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key."""
        if not self.redis_client:
            return False
        try:
            return self.redis_client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if not self.redis_client:
            return False
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.redis_client:
            return False
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False


# Singleton Redis client
redis_client = RedisClient()
