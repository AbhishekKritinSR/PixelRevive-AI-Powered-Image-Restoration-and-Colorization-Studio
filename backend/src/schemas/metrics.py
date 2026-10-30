"""Module: metrics.py

Purpose:
Defines Pydantic schemas for image evaluation and heuristic metrics.
"""

from pydantic import BaseModel, Field


class QualityMetricsResponse(BaseModel):
    """Schema representing statistical quality metrics and performance timing."""

    sharpness: float = Field(description="Variance of discrete Laplacian on result image")
    contrast: float = Field(description="Standard deviation of pixel intensities on result image")
    brightness: float = Field(description="Mean pixel intensity on result image [0.0, 255.0]")
    sharpness_delta: float = Field(description="Change in sharpness compared to input (after - before)")
    contrast_delta: float = Field(description="Change in contrast compared to input (after - before)")
    device: str = Field(description="Compute device used for processing ('CPU' or 'CUDA')")
    elapsed_seconds: float = Field(description="Total end-to-end processing latency in seconds")

