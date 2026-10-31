"""Module: restoration.py

Purpose:
Defines Pydantic request and response schemas for single-image restoration operations.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field

from .metrics import QualityMetricsResponse


class RestorationOptions(BaseModel):
    """Schema representing processing toggles for image restoration and colorization."""

    denoise: bool = Field(default=True, description="Enable Non-Local Means denoising")
    contrast: bool = Field(default=True, description="Enable CLAHE contrast enhancement on L channel")
    sharpen: bool = Field(default=True, description="Enable unity-gain Laplacian sharpening")
    colorize: bool = Field(default=True, description="Enable AI deep convolutional colorization")
    adaptive_denoise: bool = Field(
        default=True,
        description="Whether to intelligently adapt denoising strength based on image noise level (when denoise=True)",
    )
    adaptive_contrast: bool = Field(
        default=True,
        description="Whether to adaptively evaluate image contrast and bypass CLAHE on images with adequate natural dynamic range (when contrast=True)",
    )
    adaptive_sharpen: bool = Field(
        default=True,
        description="Whether to adaptively evaluate sharpness and noise to bypass unnecessary sharpening on sharp or pristine images (when sharpen=True)",
    )
    repair: bool = Field(
        default=False,
        description="Enable archival scratch repair and inpainting",
    )
    inpaint_method: str = Field(
        default="lama",
        description="Inpainting method ('lama', 'telea', 'ns')",
    )
    face_restore: bool = Field(
        default=False,
        description="Enable optional identity-preserving facial feature restoration",
    )
    upscale: bool = Field(
        default=False,
        description="Enable AI super-resolution upscaling (2x or 4x)",
    )
    scale: int = Field(
        default=2,
        description="Super-resolution scaling factor (2 or 4)",
    )
    sr_model: str = Field(
        default="fsrcnn",
        description="Super-resolution model ('fsrcnn' or 'realesrgan')",
    )
    colorization_model: str = Field(
        default="zhang_caffe",
        description="Identifier of the colorization model to use ('zhang_caffe')",
    )
    render_factor: int = Field(
        default=14,
        description="Colorization rendering factor between 10 and 40 (default 14 corresponds to native 224x224)",
    )
    color_saturation: float = Field(
        default=0.85,
        description="Chroma saturation factor (0.0 to 1.5, default 0.85 for natural historical tones)",
    )
    color_temperature: float = Field(
        default=0.0,
        description="Color temperature bias (-1.0 cool to 1.0 warm, default 0.0 neutral)",
    )


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
    operations_summary: Optional[Dict[str, str]] = Field(
        default=None,
        description="Transparent summary of operations executed or intelligently bypassed"
    )


class DamageMaskResponse(BaseModel):
    """Schema returned by POST /api/v1/restoration/mask for damage inspection."""

    status: str = Field(default="success", description="Outcome status ('success')")
    filename: str = Field(description="Original uploaded filename")
    detected_components: int = Field(description="Number of detected scratch components")
    repaired_pixels: int = Field(description="Total scratch pixel count in mask")
    coverage_percentage: float = Field(description="Fraction of image area covered by defects (%)")
    confidence_score: float = Field(default=0.0, description="Mean ridge profile flanking confidence score [0.0, 1.0]")
    dispatch_reason: Optional[str] = Field(default=None, description="Adaptive engine selection reason")
    mask_base64: str = Field(description="Binary defect mask encoded as Base64 PNG data URI")
    overlay_base64: str = Field(description="Semi-transparent visual defect overlay encoded as Base64 PNG data URI")
    elapsed_seconds: float = Field(description="Detection latency in seconds")


