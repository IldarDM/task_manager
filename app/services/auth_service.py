from datetime import timedelta
from app.core.security import create_access_token
from app.core.config import settings

class AuthService:
    @staticmethod
    def create_access_token_for_user(user_email: str) -> str:
        """Create access token for user."""
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        return create_access_token(
            subject=user_email, expires_delta=access_token_expires
        )