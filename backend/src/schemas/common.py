"""Module: common.py

Purpose:
Defines general-purpose Pydantic schemas for health, model status, and error responses.
"""

from typing import Any, Dict, List, Optional
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
    is_default: bool = Field(default=False, description="Whether this is the default model for its task")
    detail: Optional[str] = Field(default=None, description="Optional diagnostic message or instruction")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Structured model metadata and configuration")


class ModelRegistryItem(BaseModel):
    """Schema representing an individual registered model in the registry."""

    model_id: str = Field(description="Unique model identifier")
    display_name: str = Field(description="Human-readable model name")
    architecture: str = Field(description="Neural network architecture family")
    authors: str = Field(description="Original researchers or authors")
    publication: str = Field(description="Academic citation or reference")
    model_format: str = Field(description="Asset format on disk")
    supported_task: str = Field(description="Task performed by model")
    is_default: bool = Field(description="Whether this is the default model")
    files_available: bool = Field(description="Whether model asset files exist on disk")
    is_loaded: bool = Field(description="Whether model weights are loaded in memory")
    ready_for_inference: bool = Field(description="Whether model is ready to execute inference")
    supported_parameters: Dict[str, Any] = Field(default_factory=dict, description="Configurable tuning parameters")
    runtime_requirements: str = Field(description="Hardware/software runtime requirements")
    description: str = Field(default="", description="Detailed model overview")


class ModelRegistryListResponse(BaseModel):
    """Schema returned by GET /api/v1/models for model discovery."""

    default_model: str = Field(description="Identifier of the system default colorization model")
    models: List[ModelRegistryItem] = Field(description="List of all registered models")


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    detail: str = Field(description="Human-readable error description")

