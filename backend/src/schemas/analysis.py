"""Module: analysis.py

Purpose:
Defines Pydantic v2 schemas for the intelligent image analysis and recommendation engine.

Responsibilities:
- Declare structured models for noise, sharpness, contrast, and monochrome evaluations.
- Declare transparent recommendation models with rationale and evidence fields.
- Provide full schema validation and serialization for POST /api/v1/restoration/analyze.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ImageDimensions(BaseModel):
    """Schema representing uploaded and processed image pixel dimensions."""

    width: int = Field(description="Image width in pixels")
    height: int = Field(description="Image height in pixels")
    channels: int = Field(description="Number of color channels (typically 3)")
    was_resized: bool = Field(
        default=False,
        description="True if image exceeded the maximum dimension cap (1600px) and was downscaled",
    )


class NoiseAnalysis(BaseModel):
    """Schema representing blind noise variance estimation results."""

    noise_score: float = Field(
        description="Estimated noise standard deviation (sigma) via Laplacian residual operator"
    )
    noise_level: Literal["low", "medium", "high"] = Field(
        description="Empirical noise classification: 'low' (<4.0), 'medium' (4.0-10.0), 'high' (>=10.0)"
    )
    method: str = Field(
        default="laplacian_residual",
        description="Mathematical estimation algorithm used (Immerkær robust Laplacian operator)",
    )


class SharpnessAnalysis(BaseModel):
    """Schema representing high-frequency edge sharpness results."""

    sharpness_score: float = Field(
        description="Variance of discrete 2D Laplacian operator on grayscale luminance"
    )
    sharpness_level: Literal["blurry", "moderate", "sharp"] = Field(
        description="Empirical sharpness classification: 'blurry' (<100), 'moderate' (100-500), 'sharp' (>=500)"
    )


class ContrastAnalysis(BaseModel):
    """Schema representing dynamic range and contrast dispersion results."""

    contrast_score: float = Field(
        description="Standard deviation of grayscale luminance intensities"
    )
    dynamic_range: float = Field(
        description="Difference between 99th and 1st percentiles of intensity distribution [0.0, 255.0]"
    )
    contrast_level: Literal["low", "moderate", "high"] = Field(
        description="Empirical contrast classification: 'low' (<30 std dev or <100 range), 'moderate', 'high' (>=65 std dev)"
    )


class MonochromeAnalysis(BaseModel):
    """Schema representing color channel distribution and grayscale detection."""

    is_monochrome: bool = Field(
        description="True if image is detected as grayscale or near-grayscale (mean chromatic delta < 3.5)"
    )
    color_variation_score: float = Field(
        description="Mean absolute difference across R, G, B color channels"
    )
    confidence: float = Field(
        description="Heuristic confidence metric [0.5, 1.0] indicating certainty of monochrome assessment"
    )


class RecommendationItem(BaseModel):
    """Schema representing a single restoration toggle recommendation with rationale."""

    recommended: bool = Field(
        description="Whether this restoration operation is recommended based on analysis"
    )
    reason: str = Field(
        description="Human-readable explanation of why this operation is or is not recommended"
    )
    evidence: str = Field(
        description="Machine-readable rule token indicating the decision trigger"
    )


class RestorationRecommendations(BaseModel):
    """Schema grouping recommendations for all restoration pipeline stages."""

    denoise: RecommendationItem = Field(description="Recommendation for Non-Local Means denoising")
    contrast: RecommendationItem = Field(description="Recommendation for CLAHE contrast enhancement")
    sharpen: RecommendationItem = Field(description="Recommendation for unity-gain Laplacian sharpening")
    colorize: RecommendationItem = Field(description="Recommendation for AI deep colorization")
    repair: Optional[RecommendationItem] = Field(
        default=None,
        description="Recommendation for scratch detection and inpainting",
    )
    face_restore: Optional[RecommendationItem] = Field(
        default=None,
        description="Recommendation for localized identity-preserving face enhancement",
    )
    upscale: Optional[RecommendationItem] = Field(
        default=None,
        description="Recommendation for AI super-resolution upscaling (2x or 4x)",
    )


class AnalysisMetrics(BaseModel):
    """Aggregated empirical measurement metrics."""

    noise: NoiseAnalysis = Field(description="Estimated noise variance and level")
    sharpness: SharpnessAnalysis = Field(description="Estimated sharpness and level")
    contrast: ContrastAnalysis = Field(description="Estimated contrast and dynamic range")
    monochrome: MonochromeAnalysis = Field(description="Monochrome vs color classification")


class ImageAnalysisResponse(BaseModel):
    """Top-level response schema for POST /api/v1/restoration/analyze."""

    status: str = Field(default="success", description="Outcome status ('success')")
    filename: str = Field(description="Original uploaded filename")
    image: ImageDimensions = Field(description="Image dimension and sizing metadata")
    analysis: AnalysisMetrics = Field(description="Comprehensive image quality analysis")
    detected_issues: List[str] = Field(
        description="List of detected photographic degradation issues (e.g. 'High Noise', 'Monochrome')"
    )
    recommended_options: RestorationRecommendations = Field(
        description="Rule-based restoration recommendations for each pipeline stage"
    )
    degradation_category: Optional[str] = Field(
        default="general_photograph",
        description="Holistic degradation classification (e.g. 'scratched_historical', 'faded_monochrome', 'degraded_portrait', 'clean_photograph')",
    )
    elapsed_seconds: float = Field(
        description="Total duration spent executing image analysis in seconds"
    )

