"""Module: models.py

Purpose:
Endpoint for querying AI colorization model file availability and readiness.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from backend.src.api.dependencies import get_model_service
from backend.src.schemas.common import ModelRegistryListResponse, ModelStatusResponse
from backend.src.services.model_service import ModelService

router = APIRouter()


@router.get(
    "/models",
    response_model=ModelRegistryListResponse,
    summary="List Registered AI Colorization Models",
    description="Discover all registered colorization models, supported tuning parameters, and runtime availability.",
)
def list_models(
    model_service: ModelService = Depends(get_model_service),
) -> ModelRegistryListResponse:
    """Return all registered colorization models with structured metadata and availability."""
    return model_service.list_registered_models()


@router.get(
    "/models/status",
    response_model=ModelStatusResponse,
    summary="AI Model Readiness Status",
    description="Check whether AI model files exist on disk and whether they are ready for inference.",
)
def get_model_status(
    model_name: Optional[str] = Query(
        default=None,
        description="Model to inspect ('zhang_caffe', 'fsrcnn_x2', 'fsrcnn_x4'). Defaults to 'zhang_caffe'.",
    ),
    model_service: ModelService = Depends(get_model_service),
) -> ModelStatusResponse:
    """Report model presence on disk, memory initialization state, and inference readiness."""
    return model_service.get_model_status(model_name=model_name)

