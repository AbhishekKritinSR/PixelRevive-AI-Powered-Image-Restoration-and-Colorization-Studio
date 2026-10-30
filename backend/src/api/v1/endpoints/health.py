"""Module: health.py

Purpose:
Endpoint for service health inspection and hardware detection.
"""

from fastapi import APIRouter

from backend.src.core.config import settings
from backend.src.processing.evaluation.device import get_processing_device
from backend.src.schemas.common import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health and Device Status",
    description="Check backend availability and inspect the active compute device without loading AI models.",
)
def get_health() -> HealthResponse:
    """Return operational health status and active compute hardware device."""
    return HealthResponse(
        status="healthy",
        application=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        device=get_processing_device(),
    )

