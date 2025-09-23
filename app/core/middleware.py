import time
import logging
from typing import Dict, Tuple

from fastapi import Request, HTTPException, status
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class ProductionRateLimitStore:
    """Production-ready rate limiting with Redis and fallback to in-memory."""

    def __init__(self):
        self.memory_store: Dict[str, Tuple[int, float]] = {}

    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        """Check if request is within rate limit using Redis or memory fallback."""
        try:
            return self._redis_rate_limit(key, limit, window)
        except Exception as e:
            logger.warning(f"Redis rate limiting failed, using memory fallback: {e}")
            return self._memory_rate_limit(key, limit, window)

    def _redis_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Redis-based sliding window rate limiting."""
        if not redis_client.redis_client:
            raise Exception("Redis not available")

        current_time = int(time.time())
        pipeline = redis_client.redis_client.pipeline()

        pipeline.zremrangebyscore(key, 0, current_time - window)  # remove expired
        pipeline.zcard(key)  # count current
        pipeline.zadd(key, {str(current_time): current_time})  # add current
        pipeline.expire(key, window)  # set expiration

        results = pipeline.execute()
        current_count = results[1]

        return current_count < limit

    def _memory_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """In-memory rate limiting fallback."""
        current_time = time.time()
        if key not in self.memory_store:
            self.memory_store[key] = (1, current_time)
            return True

        count, first_request = self.memory_store[key]

        if current_time - first_request > window:
            self.memory_store[key] = (1, current_time)
            return True

        if count >= limit:
            return False

        self.memory_store[key] = (count + 1, first_request)
        return True


rate_limit_store = ProductionRateLimitStore()


def rate_limit_auth(request: Request) -> None:
    """Rate limit for authentication endpoints."""
    client_ip = get_remote_address(request)
    key = f"auth:{client_ip}"

    if not rate_limit_store.is_allowed(key, settings.auth_rate_limit_per_minute, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": "60"},
        )


def rate_limit_general(request: Request) -> None:
    """General API rate limit."""
    client_ip = get_remote_address(request)
    key = f"api:{client_ip}"

    if not rate_limit_store.is_allowed(key, settings.rate_limit_per_minute, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"},
        )
