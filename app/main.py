import uuid
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from fastapi.responses import JSONResponse

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
from app.core.logging import setup_logging  # <-- добавили

# ----------------- LOGGING -----------------
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="RESTful API for personal task management with team collaboration features",
    openapi_url="/api/v1/openapi.json" if settings.debug else None,
)

# ----------------- MIDDLEWARE -----------------
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = req_id
    logger.info("Incoming request %s %s | req_id=%s",
                request.method, request.url.path, req_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response

# ----------------- EXCEPTION HANDLERS -----------------
app.add_exception_handler(HTTPException, http_exception_handler)

@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    details = []
    for err in exc.errors():
        field = err.get("loc", ["body"])[-1]
        details.append({"field": str(field), "message": err.get("msg")})

    try:
        body = await request.body()
    except Exception:
        body = b""

    logger.warning(
        "422 Validation | req_id=%s | path=%s | body=%s | details=%s",
        getattr(request.state, "request_id", "-"),
        request.url.path,
        body.decode("utf-8")[:2000],
        details,
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "message": "Validation error",
            "details": details,
            "request_id": getattr(request.state, "request_id", None),
        },
    )

app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# ----------------- ROUTERS -----------------
app.include_router(auth_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")

# ----------------- SERVICE ENDPOINTS -----------------
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
