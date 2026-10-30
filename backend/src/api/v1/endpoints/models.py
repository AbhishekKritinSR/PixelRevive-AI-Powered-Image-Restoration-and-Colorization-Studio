"""Module: models.py

Purpose:
Endpoint for querying AI colorization model file availability and readiness.
"""

from fastapi import APIRouter, Depends

from backend.src.api.dependencies import get_model_service
from backend.src.schemas.common import ModelStatusResponse
from backend.src.services.model_service import ModelService

router = APIRouter()


@router.get(
    "/models/status",
    response_model=ModelStatusResponse,
    summary="AI Model Readiness Status",
    description="Check whether the Zhang Caffe colorization model files exist on disk and whether it is ready for inference.",
)
def get_model_status(
    model_service: ModelService = Depends(get_model_service),
) -> ModelStatusResponse:
    """Report model presence on disk, memory initialization state, and inference readiness."""
    return model_service.get_model_status()

