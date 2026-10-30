"""Module: batch.py

Purpose:
Defines Pydantic request and response schemas for multi-image batch operations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from .metrics import QualityMetricsResponse


class BatchItemResult(BaseModel):
    """Schema representing processing outcome for an individual file in a batch."""

    filename: str = Field(description="Original filename of this item")
    status: str = Field(description="Processing status: 'success' or 'failed'")
    original_width: Optional[int] = Field(default=None, description="Original width in pixels")
    original_height: Optional[int] = Field(default=None, description="Original height in pixels")
    processed_width: Optional[int] = Field(default=None, description="Processed width in pixels")
    processed_height: Optional[int] = Field(default=None, description="Processed height in pixels")
    elapsed_seconds: Optional[float] = Field(default=None, description="Processing duration for this file")
    metrics: Optional[QualityMetricsResponse] = Field(default=None, description="Quality metrics if successful")
    image_base64: Optional[str] = Field(default=None, description="Base64 PNG data URI if successful")
    error: Optional[str] = Field(default=None, description="Error message if processing failed")


class BatchRestorationResponse(BaseModel):
    """Schema returned by POST /api/v1/restoration/batch."""

    total_submitted: int = Field(description="Total number of files submitted in the batch")
    total_succeeded: int = Field(description="Number of files successfully processed")
    total_failed: int = Field(description="Number of files that failed processing")
    elapsed_seconds: float = Field(description="Total end-to-end execution duration for the batch")
    items: List[BatchItemResult] = Field(description="Individual results for each file in the batch")
    zip_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded ZIP archive containing all successfully processed images",
    )

