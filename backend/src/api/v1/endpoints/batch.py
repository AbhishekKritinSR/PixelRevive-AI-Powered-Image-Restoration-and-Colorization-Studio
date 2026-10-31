"""Module: batch.py

Purpose:
Endpoint for batch restoration and colorization of multiple photographs.
"""

from typing import List

from fastapi import APIRouter, Depends, File, Form, UploadFile

from backend.src.api.dependencies import get_batch_service
from backend.src.schemas.batch import BatchRestorationResponse
from backend.src.schemas.restoration import RestorationOptions
from backend.src.services.batch_service import BatchService

router = APIRouter()


@router.post(
    "/restoration/batch",
    response_model=BatchRestorationResponse,
    summary="Batch Restore and Colorize Multiple Photographs",
    description=(
        "Upload up to 10 photos simultaneously. Processes images with isolated error handling "
        "and returns individual results alongside a bundled in-memory ZIP archive."
    ),
)
def process_batch_images(
    files: List[UploadFile] = File(..., description="Up to 10 photograph files (JPG, PNG, WEBP)"),
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
    batch_service: BatchService = Depends(get_batch_service),
) -> BatchRestorationResponse:
    """Process multiple photographs in a batch.

    Executed in FastAPI's background thread pool with per-image failure isolation.
    """
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

    files_data = [(f.filename or f"image_{idx}.png", f.file.read()) for idx, f in enumerate(files)]

    return batch_service.process_batch(
        files=files_data,
        options=options,
    )

