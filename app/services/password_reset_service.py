from datetime import datetime, timedelta
from typing import Optional
import secrets
from app.core.redis_client import redis_client
from app.core.security import get_password_hash, verify_password
from app.services.email_service import email_service
from app.db.models.user import User
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class PasswordResetService:
    @staticmethod
    def generate_reset_token() -> str:
        """Generate secure reset token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    async def request_password_reset(db: Session, email: str) -> bool:
        """Request password reset and send email."""
        from app.services.user_service import UserService

        user = UserService.get_by_email(db, email)
        if not user:
            # Don't reveal if email exists or not
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return True

        # Generate reset token
        reset_token = PasswordResetService.generate_reset_token()

        # Store token in Redis with 1-hour expiration
        key = f"password_reset:{reset_token}"
        if not redis_client.set(key, user.email, ex=3600):  # 1 hour
            logger.error("Failed to store password reset token")
            return False

        # Send email
        await email_service.send_password_reset_email(
            email_to=user.email,
            reset_token=reset_token,
            user_name=user.full_name
        )

        logger.info(f"Password reset requested for user: {user.email}")
        return True

    @staticmethod
    def reset_password_with_token(
            db: Session,
            reset_token: str,
            new_password: str
    ) -> bool:
        """Reset password using reset token."""
        from app.services.user_service import UserService

        # Get email from Redis
        key = f"password_reset:{reset_token}"
        email = redis_client.get(key)

        if not email:
            logger.warning(f"Invalid or expired reset token: {reset_token[:8]}...")
            return False

        # Get user
        user = UserService.get_by_email(db, email)
        if not user:
            logger.error(f"User not found for email: {email}")
            return False

        # Update password
        user.hashed_password = get_password_hash(new_password)
        db.commit()

        # Delete reset token
        redis_client.delete(key)

        logger.info(f"Password reset completed for user: {user.email}")
        return True