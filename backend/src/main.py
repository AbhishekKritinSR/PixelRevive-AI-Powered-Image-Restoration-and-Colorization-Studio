"""Module: main.py

Purpose:
Application entry point and factory for the FastAPI backend service.

Responsibilities:
- Initialize the FastAPI application with metadata and documentation URLs.
- Configure Cross-Origin Resource Sharing (CORS) middleware.
- Register centralized domain exception handlers.
- Mount versioned API routes under the `/api/v1` prefix.
- Manage application lifespan events (logging startup and shutdown).

Command to run server locally:
    .\\.venv\\Scripts\\python.exe -m uvicorn backend.src.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.src.api.v1.api_router import api_router
from backend.src.core.config import settings
from backend.src.core.exceptions import register_exception_handlers
from backend.src.core.logging_config import setup_logging

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager logging application startup and shutdown events."""
    logger.info("Initializing %s v%s...", settings.PROJECT_NAME, settings.PROJECT_VERSION)
    logger.info("API Documentation available at: /docs and /redoc")
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


def create_application() -> FastAPI:
    """Factory function creating and configuring the FastAPI application instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description=settings.DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register custom domain exception handlers
    register_exception_handlers(app)

    # Mount version 1 API endpoints
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/", tags=["Root"], summary="API Root Status")
    def root():
        """Welcome and discovery endpoint."""
        return {
            "application": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
            "status": "online",
            "documentation": "/docs",
            "api_v1": settings.API_V1_STR,
        }

    return app


app = create_application()

