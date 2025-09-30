from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator

from app.core.deps import get_db, get_current_user
from app.core.middleware import rate_limit_auth
from app.core.exceptions import ConflictError, AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.db.schemas.user import UserCreate, UserResponse, UserLogin, UserUpdate
from app.db.schemas.token import Token
from app.db.schemas.error import SuccessResponse
from app.services.user_service import UserService
from app.services.token_service import TokenService
from app.services.password_reset_service import PasswordResetService
from app.services.email_service import email_service
from app.db.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    @validator("new_password")
    def validate_password(cls, v: str) -> str:
        from app.core.security import validate_password_strength
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError("; ".join(errors))
        return v

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(*, request: Request, db: Session = Depends(get_db), user_in: UserCreate) -> Any:
    rate_limit_auth(request)
    try:
        user = UserService.create(db=db, user_create=user_in)
        try:
            await email_service.send_welcome_email(user.email, user.full_name)
        except Exception as e:
            import logging; logging.getLogger(__name__).warning(f"Failed to send welcome email: {e}")
        return user
    except ValueError as e:
        raise ConflictError(detail=str(e))

@router.post("/login", response_model=Token, summary="Login user")
async def login(*, request: Request, db: Session = Depends(get_db), user_credentials: UserLogin) -> Any:
    rate_limit_auth(request)
    user = UserService.authenticate(db=db, email=user_credentials.email, password=user_credentials.password)
    if not user or not user.is_active:
        raise AuthenticationError(detail="Incorrect email or password" if not user else "Inactive user account")

    access_token = create_access_token(user.email)
    refresh_token = create_refresh_token(user.email)
    TokenService.store_refresh_token(refresh_token, user.email)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=Token, summary="Refresh access token")
async def refresh_tokens(*, request: Request, body: RefreshRequest) -> Any:
    rate_limit_auth(request)
    email = verify_refresh_token(body.refresh_token)
    if not email:
        raise AuthenticationError(detail="Invalid refresh token")

    owner = TokenService.get_refresh_owner(body.refresh_token)
    if owner != email:
        raise AuthenticationError(detail="Invalid or revoked refresh token")

    TokenService.revoke_refresh_token(body.refresh_token)
    new_refresh = create_refresh_token(email)
    TokenService.store_refresh_token(new_refresh, email)
    new_access = create_access_token(email)

    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse, summary="Get current user")
async def me(current_user: User = Depends(get_current_user)) -> Any:
    return current_user

@router.put("/me", response_model=UserResponse, summary="Update current user")
async def update_me(*, db: Session = Depends(get_db), user_update: UserUpdate, current_user: User = Depends(get_current_user)) -> Any:
    return UserService.update(db=db, user=current_user, user_update=user_update)

@router.post("/request-password-reset", response_model=SuccessResponse, summary="Request password reset")
async def request_password_reset(*, request: Request, db: Session = Depends(get_db), password_reset_request: PasswordResetRequest) -> Any:
    rate_limit_auth(request)
    await PasswordResetService.request_password_reset(db=db, email=password_reset_request.email)
    return SuccessResponse(message="If an account with this email exists, a password reset link has been sent.")

@router.post("/reset-password", response_model=SuccessResponse, summary="Reset password")
async def reset_password(*, request: Request, db: Session = Depends(get_db), password_reset: PasswordResetConfirm) -> Any:
    rate_limit_auth(request)
    success = PasswordResetService.reset_password_with_token(db=db, reset_token=password_reset.token, new_password=password_reset.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    return SuccessResponse(message="Password reset successfully")

class LogoutRequest(BaseModel):
    refresh_token: str | None = None

@router.post("/logout", response_model=SuccessResponse, summary="Logout user")
async def logout(request: Request, current_user: User = Depends(get_current_user), body: LogoutRequest | None = None) -> Any:
    # Отзываем access (по заголовку)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        TokenService.blacklist_token(auth_header[7:])

    # Если прислали refresh — тоже отзываем
    if body and body.refresh_token:
        TokenService.revoke_refresh_token(body.refresh_token)

    return SuccessResponse(message="Successfully logged out", data={"user_id": current_user.id})
