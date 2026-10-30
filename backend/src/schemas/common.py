"""Module: common.py

Purpose:
Defines general-purpose Pydantic schemas for health, model status, and error responses.
"""

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema returned by GET /api/v1/health."""

    status: str = Field(default="healthy", description="Service health state")
    application: str = Field(description="Application title")
    version: str = Field(description="Semantic version string")
    device: str = Field(description="Active compute execution device ('CPU' or 'CUDA')")


class ModelStatusResponse(BaseModel):
    """Schema returned by GET /api/v1/models/status."""

    model_name: str = Field(description="Unique model identifier")
    files_available: bool = Field(description="Whether required weight and config files exist on disk")
    is_loaded: bool = Field(description="Whether the neural network is currently loaded into memory")
    ready_for_inference: bool = Field(description="Whether inference can be executed immediately")
    detail: Optional[str] = Field(default=None, description="Optional diagnostic message or instruction")


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    detail: str = Field(description="Human-readable error description")

