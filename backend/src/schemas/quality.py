"""Module: quality.py

Purpose:
Defines Pydantic request and response schemas for advanced image quality assessment.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class MetricDetail(BaseModel):
    """Detailed result for an individual quality metric."""

    metric_id: str = Field(description="Unique metric identifier ('brisque', 'ssim', 'colorfulness')")
    display_name: str = Field(description="Human-readable title of the metric")
    available: bool = Field(description="Whether the metric was evaluated")
    score: Optional[float] = Field(default=None, description="Numeric score, or null if unavailable")
    interpretation: str = Field(description="Objective technical interpretation of the metric score")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional metric sub-parameters or breakdown")


class QualityImageDimensions(BaseModel):
    """Dimensions of evaluated image."""

    width: int = Field(description="Width in pixels")
    height: int = Field(description="Height in pixels")
    channels: int = Field(description="Number of color channels")


class ImageQualityAssessmentResponse(BaseModel):
    """Schema returned by POST /api/v1/restoration/quality."""

    status: str = Field(default="success", description="Outcome status ('success')")
    filename: str = Field(description="Target image filename")
    reference_filename: Optional[str] = Field(default=None, description="Reference image filename if provided")
    image: QualityImageDimensions = Field(description="Target image dimensions")
    elapsed_seconds: float = Field(description="Total assessment latency in seconds")
    metrics: Dict[str, MetricDetail] = Field(description="Structured quality, similarity, and colorfulness metrics")
