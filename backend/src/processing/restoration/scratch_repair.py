"""Module: scratch_repair.py

Purpose:
Provides archival scratch detection and inpainting reconstruction for damaged photographs.

Key Responsibilities:
- Multi-orientation directional morphological defect detection (horizontal, vertical, diagonal 45 deg, diagonal 135 deg).
- Dual-polarity defect capture (dark scratches on light regions via Black-Hat, bright scratches on dark regions via Top-Hat).
- Connected-component geometric filtering (aspect ratio, length, thickness, and ridge vs step-edge analysis to reject false positives).
- Binary repair mask generation and safety validation with maximum coverage threshold guards.
- OpenCV inpainting execution (Telea Fast Marching Method and Navier-Stokes) supporting both 3-channel BGR and 1-channel Grayscale.
- Empty mask zero-overhead no-op bypass.

Dependencies:
- cv2, numpy, dataclasses, typing
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

# Tuned defaults for archival photograph scratch detection
DEFAULT_SCRATCH_THRESHOLD: int = 25
DEFAULT_MIN_LENGTH: int = 10
DEFAULT_MIN_ASPECT_RATIO: float = 3.0
DEFAULT_MAX_THICKNESS: int = 6
MAX_REPAIR_COVERAGE: float = 0.05  # Maximum 5% of total image area marked for repair
DEFAULT_KERNEL_LENGTH: int = 11
DEFAULT_INPAINT_RADIUS: int = 3
DEFAULT_INPAINT_METHOD: str = "telea"
MAX_NEIGHBOR_IQR: float = 40.0  # Max interquartile range of neighborhood pixels to accept as ridge


@dataclass
class ScratchRepairMetadata:
    """Metadata describing the scratch detection and repair operation."""

    applied: bool = False
    detected_components: int = 0
    repaired_pixels: int = 0
    coverage_percentage: float = 0.0
    method: str = DEFAULT_INPAINT_METHOD
    radius: int = DEFAULT_INPAINT_RADIUS
    skipped: bool = False
    skip_reason: Optional[str] = None


def _is_ridge_not_step_edge(
    gray_image: np.ndarray,
    comp_mask: np.ndarray,
    max_iqr: float = MAX_NEIGHBOR_IQR,
) -> bool:
    """Determine whether an elongated component is an isolated ridge (scratch) rather than a step edge.

    True scratches cut across an otherwise continuous local region; their flanking pixels
    have a unimodal, relatively homogeneous distribution (low IQR).
    Natural edges (object silhouettes, horizon lines, building borders) separate two distinct
    brightness regions, producing high variance / large IQR in their flanking neighborhood.
    Also supports scratches cutting across lighting gradients (e.g. human face contours).
    """
    k3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(comp_mask, k3, iterations=2)
    neighborhood = cv2.subtract(dilated, comp_mask)
    neighbor_pixels = gray_image[neighborhood > 0]
    center_pixels = gray_image[comp_mask > 0]

    if len(neighbor_pixels) < 5 or len(center_pixels) < 2:
        return True

    p75 = float(np.percentile(neighbor_pixels, 75))
    p25 = float(np.percentile(neighbor_pixels, 25))
    iqr = float(p75 - p25)

    # 1. Standard check: unimodal neighborhood (low IQR)
    if iqr <= max_iqr:
        return True

    # 2. Gradient-tolerant differential check:
    # A true scratch cutting across an illumination gradient (such as a cheek or forehead)
    # is a localized extremum (contrast trough or peak) distinctly offset from its flanking envelope.
    c_med = float(np.median(center_pixels))
    f_med = float(np.median(neighbor_pixels))
    contrast = abs(c_med - f_med)
    is_extrema = (c_med < p25 - 6.0) or (c_med > p75 + 6.0)

    if is_extrema and contrast >= 15.0:
        return True

    return False


def _filter_directional_components(
    cand_mask: np.ndarray,
    gray_image: np.ndarray,
    min_length: int = DEFAULT_MIN_LENGTH,
    min_aspect_ratio: float = DEFAULT_MIN_ASPECT_RATIO,
    max_thickness: int = DEFAULT_MAX_THICKNESS,
    max_pixels: int = 5000,
    protected_zones: Optional[List[Tuple[int, int, int, int]]] = None,
) -> Tuple[np.ndarray, int]:
    """Filter candidate binary pixels into geometrically valid scratch components."""
    if np.count_nonzero(cand_mask) == 0:
        return np.zeros_like(cand_mask), 0

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cand_mask, connectivity=8)
    accepted = np.zeros_like(cand_mask)
    count = 0

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        comp_w = stats[i, cv2.CC_STAT_WIDTH]
        comp_h = stats[i, cv2.CC_STAT_HEIGHT]
        comp_left = stats[i, cv2.CC_STAT_LEFT]
        comp_top = stats[i, cv2.CC_STAT_TOP]

        if area < min_length or area > max_pixels:
            continue

        # Biological landmark protection: suppress false positives in eyes/mouth
        if protected_zones:
            cx = int(comp_left + comp_w / 2)
            cy = int(comp_top + comp_h / 2)
            is_in_protected = False
            for (zx1, zy1, zx2, zy2) in protected_zones:
                if zx1 <= cx <= zx2 and zy1 <= cy <= zy2:
                    is_in_protected = True
                    break
            if is_in_protected:
                # Unless candidate is an extreme defect (contrast > 45), protect landmark
                comp_pix = gray_image[labels == i]
                if len(comp_pix) > 0:
                    c_med = float(np.median(comp_pix))
                    if abs(c_med - 128.0) < 45.0:
                        continue

        comp_mask = (labels == i).astype(np.uint8)
        contours, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            continue

        contour = contours[0]
        if len(contour) >= 3:
            rect = cv2.minAreaRect(contour)
            rw, rh = rect[1]
            length = max(rw, rh)
            thickness = max(min(rw, rh), 1.0)
            elongation = length / thickness
        elif len(contour) == 2:
            pt1 = contour[0][0]
            pt2 = contour[1][0]
            length = float(np.linalg.norm(pt1 - pt2))
            thickness = 1.0
            elongation = length / thickness
        else:
            length = float(max(comp_w, comp_h))
            thickness = float(max(min(comp_w, comp_h), 1))
            elongation = length / thickness

        bb_aspect = max(comp_w / max(comp_h, 1), comp_h / max(comp_w, 1))
        effective_aspect = max(elongation, bb_aspect)

        # Scratches must be elongated, sufficiently long, thin, and confirmed as ridges
        if (
            effective_aspect >= min_aspect_ratio
            and length >= min_length
            and thickness <= max_thickness
            and _is_ridge_not_step_edge(gray_image, comp_mask)
        ):
            accepted[labels == i] = 255
            count += 1

    return accepted, count


def detect_scratch_mask(
    image: np.ndarray,
    threshold: int = DEFAULT_SCRATCH_THRESHOLD,
    min_length: int = DEFAULT_MIN_LENGTH,
    min_aspect_ratio: float = DEFAULT_MIN_ASPECT_RATIO,
    max_thickness: int = DEFAULT_MAX_THICKNESS,
    max_coverage: float = MAX_REPAIR_COVERAGE,
    kernel_length: int = DEFAULT_KERNEL_LENGTH,
) -> Tuple[np.ndarray, ScratchRepairMetadata]:
    """Detect scratches and localized archival defects, returning a binary repair mask and metadata.

    Args:
        image:
            Input image as a uint8 NumPy array of shape (H, W) or (H, W, 3).
        threshold:
            Intensity residual threshold for morphological difference operations.
        min_length:
            Minimum pixel length required to classify an elongated defect as a scratch.
        min_aspect_ratio:
            Minimum length-to-thickness ratio (aspect ratio) for scratch qualification.
        max_thickness:
            Maximum defect thickness in pixels (scratches are thin lines, not broad shapes).
        max_coverage:
            Maximum allowable fraction of total image pixels marked for repair (safety cap).
        kernel_length:
            Length of directional structuring elements in pixels.

    Returns:
        Tuple of (binary repair mask as uint8 array of shape (H, W), ScratchRepairMetadata).

    Raises:
        TypeError: If input is not a numpy ndarray.
        ValueError: If input dtype is not uint8 or dimensions are invalid.
    """
    if not isinstance(image, np.ndarray):
        raise TypeError("Input image must be a numpy ndarray")
    if image.dtype != np.uint8:
        raise ValueError("Input image dtype must be uint8")
    if image.ndim not in (2, 3):
        raise ValueError("Input image must be 2D (grayscale) or 3D (color)")
    if image.ndim == 3 and image.shape[2] != 3:
        raise ValueError(f"Color images must have 3 channels, got {image.shape[2]}")
    if image.shape[0] < 2 or image.shape[1] < 2:
        raise ValueError("Image dimensions must be at least 2x2")

    # 1. Grayscale representation
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    h, w = gray.shape
    total_pixels = h * w
    max_comp_pixels = int(total_pixels * max_coverage)

    # 1b. Identify facial sensitive zones (eyes/mouth) to prevent false scratch classification
    protected_zones: List[Tuple[int, int, int, int]] = []
    if image.ndim == 3:
        try:
            from .face_restorer import FaceRestorer
            faces = FaceRestorer.detect_faces(image)
            for (fx, fy, fw, fh) in faces:
                protected_zones.append((
                    fx + int(fw * 0.10),
                    fy + int(fh * 0.18),
                    fx + int(fw * 0.90),
                    fy + int(fh * 0.52),
                ))
                protected_zones.append((
                    fx + int(fw * 0.20),
                    fy + int(fh * 0.65),
                    fx + int(fw * 0.80),
                    fy + int(fh * 0.88),
                ))
        except Exception:
            pass

    # 2. Build directional structuring elements (multi-scale primary + fine)
    k_len = max(kernel_length, 3)
    k_h = np.ones((1, k_len), dtype=np.uint8)
    k_v = np.ones((k_len, 1), dtype=np.uint8)
    k_45 = np.eye(k_len, dtype=np.uint8)[::-1].copy()
    k_135 = np.eye(k_len, dtype=np.uint8).copy()

    # Fine-scale kernel for narrow hairline scratches
    k_fine = max(k_len - 4, 5)
    k_hf = np.ones((1, k_fine), dtype=np.uint8)
    k_vf = np.ones((k_fine, 1), dtype=np.uint8)

    # 3. Morphological operations
    # Black-hat (dark defects against lighter background)
    bh_h = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, k_h)
    bh_v = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, k_v)
    bh_45 = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, k_45)
    bh_135 = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, k_135)

    # Top-hat (bright defects against darker background)
    th_h = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k_h)
    th_v = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k_v)
    th_45 = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k_45)
    th_135 = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k_135)

    # 4. Orthogonal directional subtraction
    diff_dark_v = cv2.subtract(bh_h, bh_v)
    diff_dark_h = cv2.subtract(bh_v, bh_h)
    diff_dark_45 = cv2.subtract(bh_135, bh_45)
    diff_dark_135 = cv2.subtract(bh_45, bh_135)

    diff_bright_v = cv2.subtract(th_h, th_v)
    diff_bright_h = cv2.subtract(th_v, th_h)
    diff_bright_45 = cv2.subtract(th_135, th_45)
    diff_bright_135 = cv2.subtract(th_45, th_135)

    # Threshold each directional response
    _, m_dv = cv2.threshold(diff_dark_v, threshold, 255, cv2.THRESH_BINARY)
    _, m_dh = cv2.threshold(diff_dark_h, threshold, 255, cv2.THRESH_BINARY)
    _, m_d45 = cv2.threshold(diff_dark_45, threshold, 255, cv2.THRESH_BINARY)
    _, m_d135 = cv2.threshold(diff_dark_135, threshold, 255, cv2.THRESH_BINARY)

    _, m_bv = cv2.threshold(diff_bright_v, threshold, 255, cv2.THRESH_BINARY)
    _, m_bh = cv2.threshold(diff_bright_h, threshold, 255, cv2.THRESH_BINARY)
    _, m_b45 = cv2.threshold(diff_bright_45, threshold, 255, cv2.THRESH_BINARY)
    _, m_b135 = cv2.threshold(diff_bright_135, threshold, 255, cv2.THRESH_BINARY)

    # 5. Connected-component geometric filtering performed per-direction with landmark protection
    mask_v, c_v = _filter_directional_components(
        cv2.bitwise_or(m_dv, m_bv), gray, min_length, min_aspect_ratio, max_thickness, max_comp_pixels, protected_zones
    )
    mask_h, c_h = _filter_directional_components(
        cv2.bitwise_or(m_dh, m_bh), gray, min_length, min_aspect_ratio, max_thickness, max_comp_pixels, protected_zones
    )
    mask_45, c_45 = _filter_directional_components(
        cv2.bitwise_or(m_d45, m_b45), gray, min_length, min_aspect_ratio, max_thickness, max_comp_pixels, protected_zones
    )
    mask_135, c_135 = _filter_directional_components(
        cv2.bitwise_or(m_d135, m_b135), gray, min_length, min_aspect_ratio, max_thickness, max_comp_pixels, protected_zones
    )

    combined_mask = cv2.bitwise_or(mask_v, mask_h)
    combined_mask = cv2.bitwise_or(combined_mask, mask_45)
    combined_mask = cv2.bitwise_or(combined_mask, mask_135)
    total_components = c_v + c_h + c_45 + c_135

    # 6. Gentle dilation to encompass boundary penumbra
    if total_components > 0:
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        repair_mask = cv2.dilate(combined_mask, kernel_dilate, iterations=1)
    else:
        repair_mask = combined_mask

    # 7. Safety coverage validation
    repaired_pixels = int(np.count_nonzero(repair_mask))
    coverage = repaired_pixels / total_pixels

    if coverage > max_coverage:
        # Safety guard triggered: reject mask and skip repair to preserve genuine image content
        return np.zeros((h, w), dtype=np.uint8), ScratchRepairMetadata(
            applied=False,
            detected_components=total_components,
            repaired_pixels=repaired_pixels,
            coverage_percentage=round(coverage * 100, 2),
            skipped=True,
            skip_reason=(
                f"Mask coverage ({coverage * 100:.2f}%) exceeds safety threshold "
                f"({max_coverage * 100:.1f}%)"
            ),
        )

    return repair_mask, ScratchRepairMetadata(
        applied=repaired_pixels > 0,
        detected_components=total_components,
        repaired_pixels=repaired_pixels,
        coverage_percentage=round(coverage * 100, 2),
        skipped=False,
        skip_reason=None,
    )


def generate_mask_overlay(
    image: np.ndarray,
    mask: np.ndarray,
    color: Tuple[int, int, int] = (0, 0, 255),
    alpha: float = 0.55,
) -> np.ndarray:
    """Generate visual overlay of detected scratch mask on input photograph.

    Args:
        image: Original input image (BGR or grayscale uint8).
        mask: Binary damage mask (uint8, HxW).
        color: Overlay highlight color in BGR (default red: (0, 0, 255)).
        alpha: Blend opacity between 0.0 (transparent) and 1.0 (opaque).

    Returns:
        BGR uint8 image with semi-transparent damage highlighting.
    """
    if image.ndim == 2:
        base = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        base = image.copy()

    if mask is None or np.count_nonzero(mask) == 0:
        return base

    overlay = base.copy()
    overlay[mask > 0] = color

    return cv2.addWeighted(overlay, alpha, base, 1.0 - alpha, 0)


def repair_scratches(
    image: np.ndarray,
    mask: Optional[np.ndarray] = None,
    inpaint_radius: int = DEFAULT_INPAINT_RADIUS,
    method: str = DEFAULT_INPAINT_METHOD,
) -> Tuple[np.ndarray, ScratchRepairMetadata]:
    """Reconstruct scratch-damaged pixels using hybrid inpainting.

    Args:
        image:
            Input BGR or Grayscale uint8 image NumPy array.
        mask:
            Optional pre-computed binary repair mask. If None, `detect_scratch_mask()` is run.
        inpaint_radius:
            Inpainting neighborhood radius in pixels (typically 2-5, default 3).
        method:
            Inpainting algorithm: 'lama', 'telea', 'ns', or 'hybrid' / 'auto'.

    Returns:
        Tuple of (reconstructed uint8 image NumPy array, ScratchRepairMetadata).

    Raises:
        TypeError: If image or mask is not a NumPy array.
        ValueError: If dtype, dimensions, or parameters are invalid.
    """
    if not isinstance(image, np.ndarray):
        raise TypeError("Input image must be a numpy ndarray")
    if image.dtype != np.uint8:
        raise ValueError("Input image dtype must be uint8")
    if image.ndim not in (2, 3):
        raise ValueError("Input image must be 2D (grayscale) or 3D (color)")
    if image.ndim == 3 and image.shape[2] != 3:
        raise ValueError(f"Color images must have 3 channels, got {image.shape[2]}")
    if image.shape[0] < 2 or image.shape[1] < 2:
        raise ValueError("Image dimensions must be at least 2x2")

    method_clean = method.lower().strip()
    if method_clean not in ("telea", "ns", "lama", "hybrid", "auto"):
        raise ValueError(f"Unsupported inpainting method '{method}'. Choose 'lama', 'telea', 'ns', or 'hybrid'.")

    if inpaint_radius < 1:
        raise ValueError(f"Inpaint radius must be >= 1, got {inpaint_radius}")

    # Generate or validate mask
    if mask is None:
        repair_mask, meta = detect_scratch_mask(image)
    else:
        if not isinstance(mask, np.ndarray):
            raise TypeError("Mask must be a numpy ndarray")
        if mask.dtype != np.uint8:
            raise ValueError("Mask dtype must be uint8")
        if mask.ndim != 2:
            raise ValueError(f"Mask must be a 2D array, got {mask.ndim}D")
        if mask.shape[:2] != image.shape[:2]:
            raise ValueError(
                f"Mask shape {mask.shape[:2]} does not match image shape {image.shape[:2]}"
            )

        repaired_pixels = int(np.count_nonzero(mask))
        coverage = repaired_pixels / (image.shape[0] * image.shape[1])

        if coverage > MAX_REPAIR_COVERAGE:
            return image.copy(), ScratchRepairMetadata(
                applied=False,
                detected_components=1 if repaired_pixels > 0 else 0,
                repaired_pixels=repaired_pixels,
                coverage_percentage=round(coverage * 100, 2),
                method=method_clean,
                radius=inpaint_radius,
                skipped=True,
                skip_reason=(
                    f"Mask coverage ({coverage * 100:.2f}%) exceeds safety threshold "
                    f"({MAX_REPAIR_COVERAGE * 100:.1f}%)"
                ),
            )

        repair_mask = mask
        meta = ScratchRepairMetadata(
            applied=repaired_pixels > 0,
            detected_components=1 if repaired_pixels > 0 else 0,
            repaired_pixels=repaired_pixels,
            coverage_percentage=round(coverage * 100, 2),
            skipped=False,
            skip_reason=None,
        )

    # In hybrid/auto mode: determine whether to deploy fast Telea or deep LaMa
    if method_clean in ("hybrid", "auto"):
        if meta.repaired_pixels < 350 and meta.detected_components <= 3:
            chosen_engine = "telea"
        else:
            chosen_engine = "lama"
    else:
        chosen_engine = method_clean

    meta.method = chosen_engine
    meta.radius = inpaint_radius

    # If mask is empty or repair was skipped: return unchanged copy (zero overhead)
    if meta.skipped or np.count_nonzero(repair_mask) == 0:
        meta.applied = False
        return image.copy(), meta

    # Execute deep inpainting if LaMa selected
    if chosen_engine == "lama":
        try:
            from .inpainter_lama import LaMaInpainter
            lama = LaMaInpainter.get_instance()
            if lama.is_available:
                repaired_image, success = lama.inpaint(image, repair_mask)
                if success:
                    meta.applied = True
                    meta.method = "lama"
                    return repaired_image, meta
        except Exception:
            pass  # Graceful fallback to Telea below

    # Execute classical OpenCV inpainting (Telea or Navier-Stokes)
    flags = cv2.INPAINT_TELEA if chosen_engine in ("telea", "hybrid", "auto") else cv2.INPAINT_NS
    repaired_image = cv2.inpaint(image, repair_mask, inpaintRadius=inpaint_radius, flags=flags)
    meta.applied = True
    if chosen_engine == "lama":
        meta.method = "telea (fallback)"

    return repaired_image, meta
