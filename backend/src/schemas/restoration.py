"""Module: restoration.py

Purpose:
Defines Pydantic request and response schemas for single-image restoration operations.
"""

from pydantic import BaseModel, Field

from .metrics import QualityMetricsResponse


class RestorationOptions(BaseModel):
    """Schema representing processing toggles for image restoration and colorization."""

    denoise: bool = Field(default=True, description="Enable Non-Local Means denoising")
    contrast: bool = Field(default=True, description="Enable CLAHE contrast enhancement on L channel")
    sharpen: bool = Field(default=True, description="Enable unity-gain Laplacian sharpening")
    colorize: bool = Field(default=True, description="Enable AI deep convolutional colorization")


class SingleRestorationResponse(BaseModel):
    """Schema returned by POST /api/v1/restoration/process."""

    status: str = Field(default="success", description="Outcome status ('success')")
    filename: str = Field(description="Original uploaded filename")
    original_width: int = Field(description="Width of uploaded image in pixels")
    original_height: int = Field(description="Height of uploaded image in pixels")
    processed_width: int = Field(description="Width of processed result image in pixels")
    processed_height: int = Field(description="Height of processed result image in pixels")
    was_resized: bool = Field(description="True if image was downscaled to fit maximum dimension cap")
    elapsed_seconds: float = Field(description="Total processing latency in seconds")
    options_applied: RestorationOptions = Field(description="Summary of restoration toggles applied")
    metrics: QualityMetricsResponse = Field(description="Image evaluation metrics and before/after deltas")
    image_base64: str = Field(description="Result image encoded as a Base64 PNG data URI")

