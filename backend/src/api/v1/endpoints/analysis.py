"""Module: analysis.py

Purpose:
Endpoint for analyzing photographic image degradation and generating rule-based restoration recommendations.
"""

from fastapi import APIRouter, Depends, File, UploadFile

from backend.src.api.dependencies import get_analysis_service
from backend.src.schemas.analysis import ImageAnalysisResponse
from backend.src.services.analysis_service import AnalysisService

router = APIRouter()


@router.post(
    "/restoration/analyze",
    response_model=ImageAnalysisResponse,
    summary="Analyze Photographic Image and Generate Recommendations",
    description=(
        "Upload a photo (JPG, PNG, or WEBP) to perform diagnostic image analysis. "
        "Evaluates noise variance, sharpness, dynamic range, and monochrome status, "
        "returning transparent rule-based restoration recommendations without executing any filtering."
    ),
)
def analyze_image(
    file: UploadFile = File(..., description="Photographic image file (JPG, PNG, WEBP)"),
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> ImageAnalysisResponse:
    """Analyze image quality and compute recommended restoration options.

    Executed in FastAPI's worker thread pool to avoid blocking the event loop.
    Does NOT modify the uploaded image or execute any restoration stages.
    """
    file_bytes = file.file.read()
    filename = file.filename or "upload.png"

    return analysis_service.analyze_image(
        file_bytes=file_bytes,
        filename=filename,
    )

