import logging
from typing import Union

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.schemas.error import ErrorResponse, ErrorDetail

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=exc.detail,
            details=[ErrorDetail(type="http_error", message=exc.detail)],
        ).model_dump(),
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError],
) -> JSONResponse:
    """Handle validation errors."""
    details = []

    for error in exc.errors():
        field = ".".join(str(loc) for loc in error.get("loc", [])) if error.get("loc") else None
        details.append(
            ErrorDetail(
                type="validation_error",
                message=error["msg"],
                field=field,
            )
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            message="Validation error",
            details=details,
        ).model_dump(),
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy errors."""
    logger.error(f"Database error: {exc}")

    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(
                message="Database constraint violation",
                details=[ErrorDetail(type="integrity_error", message="Resource conflict")],
            ).model_dump(),
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            message="Internal server error",
            details=[ErrorDetail(type="database_error", message="Database operation failed")],
        ).model_dump(),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            message="Internal server error",
            details=[ErrorDetail(type="server_error", message="An unexpected error occurred")],
        ).model_dump(),
    )
