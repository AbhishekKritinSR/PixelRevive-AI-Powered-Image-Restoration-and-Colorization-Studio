"""Module: quality.py

Purpose:
FastAPI endpoint for multi-metric photographic image quality assessment.
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile

from backend.src.api.dependencies import get_quality_service
from backend.src.schemas.quality import ImageQualityAssessmentResponse
from backend.src.services.quality_service import QualityService

router = APIRouter()


@router.post(
    "/restoration/quality",
    response_model=ImageQualityAssessmentResponse,
    summary="Advanced Image Quality and Similarity Assessment",
    description=(
        "Assess photograph quality using no-reference perceptual distortion (BRISQUE), "
        "structural similarity against an optional reference image (SSIM), and chromatic variance (Colorfulness). "
        "Does not perform image restoration or modify image pixels."
    ),
)
def assess_image_quality(
    file: UploadFile = File(..., description="Target photographic image file (JPG, PNG, WEBP)"),
    reference_file: Optional[UploadFile] = File(
        default=None,
        description="Optional reference image for structural similarity (SSIM) comparison",
    ),
    quality_service: QualityService = Depends(get_quality_service),
) -> ImageQualityAssessmentResponse:
    """Evaluate target image quality metrics and optional structural similarity."""
    file_bytes = file.file.read()
    filename = file.filename or "target.png"

    ref_bytes = None
    ref_filename = None
    if reference_file is not None and reference_file.filename:
        ref_bytes = reference_file.file.read()
        ref_filename = reference_file.filename

    return quality_service.assess_quality(
        file_bytes=file_bytes,
        filename=filename,
        reference_bytes=ref_bytes,
        reference_filename=ref_filename,
    )
