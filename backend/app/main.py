"""
Main FastAPI application entry point for ShopOps Agent.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.supabase import (
    SupabaseError,
    SupabaseQueryError,
    SupabaseUnavailableError,
)
from app.api.v1.router import api_router
from app.services.agent import (
    GeminiServiceError,
    GeminiUnavailableError,
)
from app.services.approval import (
    ApprovalNotFoundError,
    InvalidStateTransitionError,
    NoReorderNeededError,
)
from app.services.execution import (
    DuplicateExecutionError,
    InvalidExecutionStateError,
    TaskNotFoundError,
    TaskPersistenceError,
)
from app.services.inventory import (
    DuplicateSKUError,
    FirebaseUnavailableError,
    ProductNotFoundError,
)

logger = logging.getLogger("shopops.api")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Inner middleware: catch unhandled server exceptions so that 500 error responses
# are properly formatted as JSON and wrapped by CORSMiddleware.
@app.middleware("http")
async def unhandled_exception_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error("Unhandled server exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )


# Configure Cross-Origin Resource Sharing (CORS)
# Registered AFTER inner middleware so CORSMiddleware wraps outermost in user_middleware,
# ensuring all responses (including 500 and 502 error responses) include CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(ProductNotFoundError)
async def product_not_found_handler(request: Request, exc: ProductNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(ApprovalNotFoundError)
async def approval_not_found_handler(request: Request, exc: ApprovalNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(request: Request, exc: TaskNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvalidStateTransitionError)
async def invalid_state_transition_handler(
    request: Request, exc: InvalidStateTransitionError
):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvalidExecutionStateError)
async def invalid_execution_state_handler(
    request: Request, exc: InvalidExecutionStateError
):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(DuplicateExecutionError)
async def duplicate_execution_handler(
    request: Request, exc: DuplicateExecutionError
):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(NoReorderNeededError)
async def no_reorder_needed_handler(request: Request, exc: NoReorderNeededError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(DuplicateSKUError)
async def duplicate_sku_handler(request: Request, exc: DuplicateSKUError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(TaskPersistenceError)
async def task_persistence_error_handler(
    request: Request, exc: TaskPersistenceError
):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )


@app.exception_handler(FirebaseUnavailableError)
async def firebase_unavailable_handler(request: Request, exc: FirebaseUnavailableError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)},
    )


@app.exception_handler(SupabaseUnavailableError)
async def supabase_unavailable_handler(request: Request, exc: SupabaseUnavailableError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)},
    )


@app.exception_handler(SupabaseQueryError)
async def supabase_query_error_handler(request: Request, exc: SupabaseQueryError):
    logger.error("Supabase query error: %s", exc)
    status_code = (
        exc.status_code
        if 400 <= exc.status_code < 600
        else status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    detail = "Database service error." if status_code >= 500 else str(exc)
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )


@app.exception_handler(SupabaseError)
async def supabase_error_handler(request: Request, exc: SupabaseError):
    logger.error("Supabase error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database operation failed."},
    )


@app.exception_handler(GeminiUnavailableError)
async def gemini_unavailable_handler(request: Request, exc: GeminiUnavailableError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)},
    )


@app.exception_handler(GeminiServiceError)
async def gemini_service_error_handler(request: Request, exc: GeminiServiceError):
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": str(exc)},
    )


# Mount versioned API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["General"])
def root():
    """Returns basic application metadata and links."""
    return {
        "name": settings.PROJECT_NAME,
        "description": settings.PROJECT_DESCRIPTION,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs",
        "health_url": "/health",
        "api_v1_prefix": settings.API_V1_PREFIX,
    }


@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint to verify backend service status.
    Independent of external credentials (Firebase, Gemini) so it always reports status reliably.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }
