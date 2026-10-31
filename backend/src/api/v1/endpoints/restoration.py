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
    upscale: bool = Form(
        default=False,
        description="Apply AI super-resolution upscaling (2x or 4x)",
    ),
    scale: int = Form(
        default=2,
        description="Super-resolution scaling factor (2 or 4)",
    ),
    colorization_model: str = Form(
        default="zhang_caffe",
        description="Colorization model identifier ('zhang_caffe')",
    ),
    render_factor: int = Form(
        default=14,
        description="Colorization rendering factor (10 to 40, default 14)",
    ),
    inpaint_method: str = Form(
        default="lama",
        description="Inpainting method ('lama', 'telea', 'ns')",
    ),
    face_restore: bool = Form(
        default=False,
        description="Apply identity-preserving face enhancement",
    ),
    sr_model: str = Form(
        default="fsrcnn",
        description="Super-resolution model ('fsrcnn' or 'realesrgan')",
    ),
    color_saturation: float = Form(
        default=0.85,
        description="Color saturation factor (0.0 to 1.5, default 0.85)",
    ),
    color_temperature: float = Form(
        default=0.0,
        description="Color temperature bias (-1.0 cool to 1.0 warm, default 0.0)",
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
        inpaint_method=inpaint_method,
        face_restore=face_restore,
        upscale=upscale,
        scale=scale,
        sr_model=sr_model,
        colorization_model=colorization_model,
        render_factor=render_factor,
        color_saturation=color_saturation,
        color_temperature=color_temperature,
    )

    response, _ = restoration_service.process_image(
        file_bytes=file_bytes,
        filename=filename,
        options=options,
    )

    return response

