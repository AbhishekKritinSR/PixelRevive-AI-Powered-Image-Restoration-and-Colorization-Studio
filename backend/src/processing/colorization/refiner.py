"""Module: refiner.py

Purpose:
Provides post-inference chrominance refinement for deep neural colorization models.
Eliminates unnatural color bleeding, garish oversaturation, and shadow color artifacts
using guided filtering, temperature compensation, and luminance-conditioned attenuation.

Academic Mapping:
- VIT BCSE403L Module 4: Image Restoration and Color Image Processing (CIE LAB chrominance,
  edge-preserving cross-bilateral/guided filtering, perceptual color balance).
"""

from typing import Optional, Tuple
import cv2
import numpy as np


class NaturalChrominanceRefiner:
    """Refines predicted CIE LAB chrominance channels (ab) using structural guidance from Lightness (L)."""

    def __init__(
        self,
        saturation: float = 0.85,
        color_temperature: float = 0.0,
        edge_refinement: bool = True,
        shadow_attenuation: bool = True,
        guided_radius: int = 6,
        guided_eps: float = 100.0,
    ):
        self.saturation = float(saturation)
        self.color_temperature = float(color_temperature)
        self.edge_refinement = bool(edge_refinement)
        self.shadow_attenuation = bool(shadow_attenuation)
        self.guided_radius = int(guided_radius)
        self.guided_eps = float(guided_eps)

    def refine(
        self,
        L: np.ndarray,
        ab: np.ndarray,
    ) -> np.ndarray:
        """Apply the full refinement cascade to (a, b) chrominance channels.

        Args:
            L: Lightness channel, float32 or uint8 array of shape (H, W), values in [0.0, 100.0].
            ab: Predicted chrominance channels, float32 array of shape (H, W, 2).

        Returns:
            Refined chrominance channels, float32 array of shape (H, W, 2).
        """
        return refine_chrominance(
            L=L,
            ab=ab,
            saturation=self.saturation,
            color_temperature=self.color_temperature,
            edge_refinement=self.edge_refinement,
            shadow_attenuation=self.shadow_attenuation,
            guided_radius=self.guided_radius,
            guided_eps=self.guided_eps,
        )


def refine_chrominance(
    L: np.ndarray,
    ab: np.ndarray,
    saturation: float = 0.85,
    color_temperature: float = 0.0,
    edge_refinement: bool = True,
    shadow_attenuation: bool = True,
    guided_radius: int = 6,
    guided_eps: float = 100.0,
) -> np.ndarray:
    """Refine raw neural colorization chrominance predictions.

    1. Edge-Preserving Structural Snapping:
       Uses OpenCV guided filtering conditioned on the uncorrupted Lightness (L)
       channel to align chrominance transitions to actual physical object contours,
       eliminating color bleeding across object boundaries.
    2. Temperature / White Balance Tuning:
       Adjusts (a, b) coordinates along the Planckian locus approximation:
       positive values warm tones (amber/sepia), negative values cool tones (cyan/blue).
    3. Restrained Natural Saturation Scaling:
       Scales chroma coordinates to prevent garish or synthetic hypersaturation.
    4. Shadow and Specular Highlight Desaturation:
       Fades chroma towards neutral gray in extreme shadows (L < 8) and highlights (L > 95)
       to avoid color staining on deep blacks and blown whites.

    Args:
        L: Lightness channel (H, W), float32 with values in [0.0, 100.0].
        ab: Chrominance channels (H, W, 2), float32.
        saturation: Chroma scale multiplier (0.85 default for restrained historical tones).
        color_temperature: Temperature shift between -1.0 (cool) and 1.0 (warm).
        edge_refinement: Whether to perform guided filter edge snapping.
        shadow_attenuation: Whether to desaturate deep shadows and specular highlights.
        guided_radius: Filter window radius for guided filtering.
        guided_eps: Regularization parameter for guided filtering.

    Returns:
        Refined (a, b) chrominance channels as float32 array of shape (H, W, 2).
    """
    refined_ab = ab.copy()

    # 1. Edge-Preserving Chrominance Alignment (Guided Filtering)
    if edge_refinement:
        if hasattr(cv2, "ximgproc") and hasattr(cv2.ximgproc, "guidedFilter"):
            try:
                L_guide = np.clip(L * 2.55, 0, 255).astype(np.uint8)
                ab_a = np.ascontiguousarray(refined_ab[:, :, 0], dtype=np.float32)
                ab_b = np.ascontiguousarray(refined_ab[:, :, 1], dtype=np.float32)
                a_ref = cv2.ximgproc.guidedFilter(
                    guide=L_guide, src=ab_a, radius=guided_radius, eps=guided_eps
                )
                b_ref = cv2.ximgproc.guidedFilter(
                    guide=L_guide, src=ab_b, radius=guided_radius, eps=guided_eps
                )
                refined_ab = np.stack([a_ref, b_ref], axis=2)
            except Exception:
                pass
        else:
            # Graceful bilateral fallback if ximgproc is not compiled
            try:
                a_ref = cv2.bilateralFilter(refined_ab[:, :, 0].astype(np.float32), d=5, sigmaColor=15.0, sigmaSpace=5.0)
                b_ref = cv2.bilateralFilter(refined_ab[:, :, 1].astype(np.float32), d=5, sigmaColor=15.0, sigmaSpace=5.0)
                refined_ab = np.stack([a_ref, b_ref], axis=2)
            except Exception:
                pass

    # 2. Temperature and White Balance Compensation
    if color_temperature != 0.0:
        refined_ab[:, :, 1] += float(color_temperature * 4.0)
        refined_ab[:, :, 0] += float(color_temperature * 1.5)

    # 3. Saturation Tuning in CIE LAB Space
    if saturation != 1.0 and saturation >= 0.0:
        refined_ab = refined_ab * float(saturation)

    # 4. Shadow and Highlight Desaturation to Prevent Chromatic Blotches
    if shadow_attenuation:
        fade = np.clip((L - 8.0) / 12.0, 0.0, 1.0) * np.clip((95.0 - L) / 8.0, 0.0, 1.0)
        refined_ab = refined_ab * fade[:, :, np.newaxis]

    return refined_ab
