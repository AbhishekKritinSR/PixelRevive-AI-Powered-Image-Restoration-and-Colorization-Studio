"""Module: restoration.py

Purpose:
Endpoint for processing and restoring a single photographic image.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile

from backend.src.api.dependencies import get_restoration_service
from backend.src.schemas.restoration import (
    RestorationOptions,
    SingleRestorationResponse,
)
from backend.src.services.restoration_service import RestorationService

router = APIRouter()


@router.post(
    "/restoration/process",
    response_model=SingleRestorationResponse,
    summary="Restore and Colorize a Single Photograph",
    description=(
        "Upload a photo (JPG, PNG, or WEBP) and apply classical image restoration "
        "(denoising, CLAHE contrast enhancement, Laplacian sharpening) and/or AI colorization."
    ),
)
def process_single_image(
    file: UploadFile = File(..., description="Photographic image file (JPG, PNG, WEBP)"),
    denoise: bool = Form(default=True, description="Apply Non-Local Means denoising"),
    contrast: bool = Form(default=True, description="Apply CLAHE contrast enhancement on L channel"),
    sharpen: bool = Form(default=True, description="Apply unity-gain Laplacian sharpening"),
    colorize: bool = Form(default=True, description="Apply AI deep convolutional colorization"),
    adaptive_denoise: bool = Form(
        default=True,
        description="Intelligently adapt denoising strength based on estimated image noise level (when denoise is True)",
    ),
    repair: bool = Form(
        default=False,
        description="Apply archival scratch detection and inpainting",
    ),
    restoration_service: RestorationService = Depends(get_restoration_service),
) -> SingleRestorationResponse:
    """Restore and colorize an individual photograph.

    Executed in FastAPI's background thread pool to avoid blocking the async event loop.
    """
    file_bytes = file.file.read()
    filename = file.filename or "upload.png"

    options = RestorationOptions(
        denoise=denoise,
        contrast=contrast,
        sharpen=sharpen,
        colorize=colorize,
        adaptive_denoise=adaptive_denoise,
        repair=repair,
    )

    response, _ = restoration_service.process_image(
        file_bytes=file_bytes,
        filename=filename,
        options=options,
    )

    return response

