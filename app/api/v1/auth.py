from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.deps import get_db, get_current_user
from app.core.middleware import rate_limit_auth
from app.core.exceptions import ConflictError, AuthenticationError
from app.db.schemas.user import UserCreate, UserResponse, UserLogin, UserUpdate
from app.db.schemas.token import Token
from app.db.schemas.error import ErrorResponse, SuccessResponse
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.services.token_service import TokenService
from app.services.password_reset_service import PasswordResetService
from app.services.email_service import email_service
from app.db.models.user import User
from pydantic import BaseModel, EmailStr, validator
from typing import Any

router = APIRouter(prefix="/auth", tags=["Authentication"])


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @validator('new_password')
    def validate_password(cls, v):
        from app.core.security import validate_password_strength
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError('; '.join(errors))
        return v


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account with email and password"
)
async def register(
        *,
        request: Request,
        db: Session = Depends(get_db),
        user_in: UserCreate,
) -> Any:
    """Register a new user."""
    rate_limit_auth(request)

    try:
        user = UserService.create(db=db, user_create=user_in)

        # Send welcome email (async, don't block registration)
        try:
            await email_service.send_welcome_email(user.email, user.full_name)
        except Exception as e:
            # Log but don't fail registration
            import logging
            logging.getLogger(__name__).warning(f"Failed to send welcome email: {e}")

        return user
    except ValueError as e:
        raise ConflictError(detail=str(e))


@router.post(
    "/login",
    response_model=Token,
    summary="Login user",
    description="Authenticate user and return JWT access token"
)
async def login(
        *,
        request: Request,
        db: Session = Depends(get_db),
        user_credentials: UserLogin,
) -> Any:
    """Login user and return access token."""
    rate_limit_auth(request)

    user = UserService.authenticate(
        db=db,
        email=user_credentials.email,
        password=user_credentials.password
    )

    if not user:
        raise AuthenticationError(detail="Incorrect email or password")

    if not user.is_active:
        raise AuthenticationError(detail="Inactive user account")

    access_token = AuthService.create_access_token_for_user(user.email)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user information"
)
async def get_current_user_info(
        current_user: User = Depends(get_current_user),
) -> Any:
    """Get current user information."""
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    description="Update current user profile information"
)
async def update_current_user(
        *,
        db: Session = Depends(get_db),
        user_update: UserUpdate,
        current_user: User = Depends(get_current_user),
) -> Any:
    """Update current user information."""
    user = UserService.update(db=db, user=current_user, user_update=user_update)
    return user


@router.post(
    "/request-password-reset",
    response_model=SuccessResponse,
    summary="Request password reset",
    description="Request password reset email"
)
async def request_password_reset(
        *,
        request: Request,
        db: Session = Depends(get_db),
        password_reset_request: PasswordResetRequest,
) -> Any:
    """Request password reset."""
    rate_limit_auth(request)

    await PasswordResetService.request_password_reset(
        db=db,
        email=password_reset_request.email
    )

    return SuccessResponse(
        message="If an account with this email exists, a password reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=SuccessResponse,
    summary="Reset password",
    description="Reset password using reset token"
)
async def reset_password(
        *,
        request: Request,
        db: Session = Depends(get_db),
        password_reset: PasswordResetConfirm,
) -> Any:
    """Reset password using token."""
    rate_limit_auth(request)

    success = PasswordResetService.reset_password_with_token(
        db=db,
        reset_token=password_reset.token,
        new_password=password_reset.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    return SuccessResponse(
        message="Password reset successfully"
    )


@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="Logout user",
    description="Logout current user and blacklist token"
)
async def logout(
        request: Request,
        current_user: User = Depends(get_current_user),
) -> Any:
    """Logout user and blacklist token."""
    # Extract token from Authorization header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        TokenService.blacklist_token(token)

    return SuccessResponse(
        message="Successfully logged out",
        data={"user_id": current_user.id}
    )