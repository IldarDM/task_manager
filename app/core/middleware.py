import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)


class ProductionRateLimitStore:
    """Production-ready rate limiting with Redis fallback to in-memory."""

    def __init__(self):
        self.memory_store: Dict[str, Tuple[int, float]] = {}

    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        """Check if request is within rate limit using Redis or fallback to memory."""
        try:
            return self._redis_rate_limit(key, limit, window)
        except Exception as e:
            logger.warning(f"Redis rate limiting failed, falling back to memory: {e}")
            return self._memory_rate_limit(key, limit, window)

    def _redis_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Redis-based sliding window rate limiting."""
        if not redis_client.redis_client:
            raise Exception("Redis not available")

        current_time = int(time.time())
        pipeline = redis_client.redis_client.pipeline()

        # Remove expired entries
        pipeline.zremrangebyscore(key, 0, current_time - window)

        # Count current requests
        pipeline.zcard(key)

        # Add current request
        pipeline.zadd(key, {str(current_time): current_time})

        # Set expiration
        pipeline.expire(key, window)

        results = pipeline.execute()
        current_count = results[1]

        return current_count < limit

    def _memory_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """In-memory rate limiting as fallback."""
        current_time = time.time()

        if key not in self.memory_store:
            self.memory_store[key] = (1, current_time)
            return True

        count, first_request = self.memory_store[key]

        # Reset if window has passed
        if current_time - first_request > window:
            self.memory_store[key] = (1, current_time)
            return True

        # Check if limit exceeded
        if count >= limit:
            return False

        # Increment counter
        self.memory_store[key] = (count + 1, first_request)
        return True


rate_limit_store = ProductionRateLimitStore()


def rate_limit_auth(request: Request) -> None:
    """Rate limit for authentication endpoints."""
    client_ip = get_remote_address(request)

    if not rate_limit_store.is_allowed(
            f"auth:{client_ip}",
            settings.auth_rate_limit_per_minute,
            60
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": "60"}
        )


def rate_limit_general(request: Request) -> None:
    """General rate limit for API endpoints."""
    client_ip = get_remote_address(request)

    if not rate_limit_store.is_allowed(
            f"api:{client_ip}",
            settings.rate_limit_per_minute,
            60
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"}
        )