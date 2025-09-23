from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler
)
from app.api.v1.auth import router as auth_router
from app.api.v1.categories import router as categories_router
from app.api.v1.tasks import router as tasks_router

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="RESTful API for personal task management with team collaboration features",
    openapi_url="/api/v1/openapi.json" if settings.debug else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Returns service health and version info."""
    return {
        "status": "healthy",
        "version": settings.version,
        "app": settings.app_name,
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint showing basic info."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "docs_url": "/docs" if settings.debug else None,
    }
