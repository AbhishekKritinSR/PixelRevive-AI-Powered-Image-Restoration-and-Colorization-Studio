"""Module: exceptions.py

Purpose:
Defines custom domain exception classes and provides centralized FastAPI
exception handlers that map domain errors to clean, informative HTTP status codes.

Responsibilities:
- Declare typed domain exceptions for image validation, size limits, and model readiness.
- Provide HTTP exception handlers that prevent leaking internal traces or file paths.
- Ensure standard JSON error format: {"detail": "..."}.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class ImageValidationError(Exception):
    """Base exception for image ingestion and decoding failures."""
    pass


class CorruptedImageError(ImageValidationError):
    """Raised when an uploaded file cannot be decoded as a valid image."""
    pass


class UnsupportedFormatError(ImageValidationError):
    """Raised when an uploaded file format is not supported."""
    pass


class FileTooLargeError(ImageValidationError):
    """Raised when an uploaded file exceeds the maximum allowed byte size."""
    pass


class BatchSizeExceededError(Exception):
    """Raised when a batch upload request exceeds the maximum file limit."""
    pass


class ModelUnavailableError(Exception):
    """Raised when an AI model is requested but its required files are missing or uninitialized."""
    pass


class UnsupportedScaleError(Exception):
    """Raised when an unsupported super-resolution scaling factor is requested."""
    pass


class SuperResolutionResourceError(Exception):
    """Raised when super-resolution output dimensions or memory exceed safety limits."""
    pass


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI application instance.

    Args:
        app:
            The FastAPI application instance.
    """

    @app.exception_handler(CorruptedImageError)
    async def corrupted_image_handler(request: Request, exc: CorruptedImageError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(UnsupportedFormatError)
    async def unsupported_format_handler(request: Request, exc: UnsupportedFormatError):
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={"detail": str(exc)},
        )

    @app.exception_handler(FileTooLargeError)
    async def file_too_large_handler(request: Request, exc: FileTooLargeError):
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": str(exc)},
        )

    @app.exception_handler(BatchSizeExceededError)
    async def batch_size_handler(request: Request, exc: BatchSizeExceededError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ModelUnavailableError)
    async def model_unavailable_handler(request: Request, exc: ModelUnavailableError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": str(exc)},
        )

    @app.exception_handler(UnsupportedScaleError)
    async def unsupported_scale_handler(request: Request, exc: UnsupportedScaleError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(SuperResolutionResourceError)
    async def super_res_resource_handler(request: Request, exc: SuperResolutionResourceError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

