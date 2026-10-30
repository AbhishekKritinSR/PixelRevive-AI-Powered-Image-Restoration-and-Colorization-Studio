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
    )

    files_data = [(f.filename or f"image_{idx}.png", f.file.read()) for idx, f in enumerate(files)]

    return batch_service.process_batch(
        files=files_data,
        options=options,
    )

