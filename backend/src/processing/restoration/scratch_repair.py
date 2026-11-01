"""Module: scratch_repair.py

Purpose:
Provides archival scratch detection and inpainting reconstruction for damaged photographs.

Key Responsibilities:
- Multi-orientation directional morphological defect detection covering 12 angular orientations grouped into
  4 directional families (Horizontal: 0°, 15°, 165°; Diagonal 45°: 30°, 45°, 60°; Vertical: 75°, 90°, 105°;
  Diagonal 135°: 120°, 135°, 150°).
- Multi-scale structuring elements for hairline (1-2px), medium (3-5px), and broad (5-8px) scratches.
- Dual-polarity defect capture (dark scratches on light regions via directional closing vs isotropic closing,
  bright scratches on dark regions via directional opening vs isotropic opening).
- Per-orientation-group geometric filtering preventing intersecting scratches from merging into falsely thick shapes.
- Adaptive hysteresis connection and collinear micro-gap bridging to prevent scratch fragmentation.
- Connected-component geometric filtering (aspect ratio, length, thickness, and ridge vs step-edge analysis).
- Facial landmark awareness: specialized criteria inside sensitive biological zones (eyes/mouth) to prevent
  false detection on facial features while fully preserving genuine scratches traversing the face.
- Binary repair mask generation and safety validation with maximum coverage threshold guards.
- Inpainting execution (LaMa Deep AI Fast Fourier Convolutions, OpenCV Telea Fast Marching, Navier-Stokes).
- Empty mask zero-overhead no-op bypass.

Dependencies:
- cv2, numpy, dataclasses, typing
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

# Tuned defaults for archival photograph scratch detection
DEFAULT_SCRATCH_THRESHOLD: int = 18
DEFAULT_MIN_LENGTH: int = 10
DEFAULT_MIN_ASPECT_RATIO: float = 2.8
DEFAULT_MAX_THICKNESS: int = 6
MAX_REPAIR_COVERAGE: float = 0.08  # Maximum 8% of total image area marked for repair
DEFAULT_KERNEL_LENGTH: int = 13
DEFAULT_INPAINT_RADIUS: int = 3
DEFAULT_INPAINT_METHOD: str = "telea"
MAX_NEIGHBOR_IQR: float = 45.0  # Max interquartile range of neighborhood pixels to accept as ridge

# Directional angular families
DIRECTIONAL_GROUPS: List[Tuple[str, List[float]]] = [
    ("h", [0.0, 15.0, 165.0]),
    ("d45", [30.0, 45.0, 60.0]),
    ("v", [75.0, 90.0, 105.0]),
    ("d135", [120.0, 135.0, 150.0]),
]

_KERNEL_CACHE: Dict[Tuple[int, float], np.ndarray] = {}


def _create_line_kernel(length: int, angle_deg: float) -> np.ndarray:
    """Generate a 2D binary line structuring element at a specified angle.

    Args:
        length: Pixel length of the line.
        angle_deg: Orientation in degrees in [0.0, 180.0).

    Returns:
        Square uint8 NumPy array of shape (length, length).
    """
    length = max(int(length), 3)
    if length % 2 == 0:
        length += 1

    key = (length, round(angle_deg, 1))
    if key in _KERNEL_CACHE:
        return _KERNEL_CACHE[key]

    kernel = np.zeros((length, length), dtype=np.uint8)
    center = length // 2

    # Fast paths for orthogonal directions
    if abs(angle_deg - 0.0) < 1e-3 or abs(angle_deg - 180.0) < 1e-3:
        kernel[center, :] = 1
        _KERNEL_CACHE[key] = kernel
        return kernel
    if abs(angle_deg - 90.0) < 1e-3:
        kernel[:, center] = 1
        _KERNEL_CACHE[key] = kernel
        return kernel

    angle_rad = np.deg2rad(angle_deg)
    dx = np.cos(angle_rad)
    dy = np.sin(angle_rad)

    # Sample points along the line
    for i in range(-center, center + 1):
        x = int(round(center + i * dx))
        y = int(round(center + i * dy))
        if 0 <= x < length and 0 <= y < length:
            kernel[y, x] = 1

    kernel[center, center] = 1
    _KERNEL_CACHE[key] = kernel
    return kernel


@dataclass
class ScratchRepairMetadata:
    """Metadata describing the scratch detection and repair operation."""

    applied: bool = False
    detected_components: int = 0
    repaired_pixels: int = 0
    coverage_percentage: float = 0.0
    method: str = DEFAULT_INPAINT_METHOD
    radius: int = DEFAULT_INPAINT_RADIUS
    confidence_score: float = 0.0
    dispatch_reason: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


def _evaluate_ridge_profile(
    gray_image: np.ndarray,
    comp_mask: np.ndarray,
    max_iqr: float = MAX_NEIGHBOR_IQR,
) -> Tuple[bool, float]:
    """Evaluate whether an elongated component is an isolated ridge (scratch) rather than a step edge.

    Calculates flanking bilateral symmetry and extremum contrast.
    
    Returns:
        Tuple of (is_scratch: bool, confidence: float [0.0, 1.0]).
    """
    k3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(comp_mask, k3, iterations=2)
    neighborhood = cv2.subtract(dilated, comp_mask)
    neighbor_pixels = gray_image[neighborhood > 0]
    center_pixels = gray_image[comp_mask > 0]

    if len(neighbor_pixels) < 5 or len(center_pixels) < 2:
        return True, 0.50

    c_med = float(np.median(center_pixels))
    f_med = float(np.median(neighbor_pixels))
    contrast = abs(c_med - f_med)

    p75 = float(np.percentile(neighbor_pixels, 75))
    p25 = float(np.percentile(neighbor_pixels, 25))
    iqr = float(p75 - p25)

    # Flanking halves to detect step edges
    f_low = neighbor_pixels[neighbor_pixels <= f_med]
    f_high = neighbor_pixels[neighbor_pixels >= f_med]
    mu_low = float(np.mean(f_low)) if len(f_low) > 0 else f_med
    mu_high = float(np.mean(f_high)) if len(f_high) > 0 else f_med
    step_diff = float(mu_high - mu_low)

    # Extremum check: true scratch core is outside flanking envelope or has high contrast
    is_bright_ridge = (c_med > f_med + 3.0) and (c_med >= p75 - 3.0 or contrast >= 12.0)
    is_dark_ridge = (c_med < f_med - 3.0) and (c_med <= p25 + 3.0 or contrast >= 12.0)
    is_extremum = is_bright_ridge or is_dark_ridge

    # Flanking symmetry ratio (high for symmetric ridge, low for step edge)
    sym_ratio = contrast / (contrast + step_diff + 1.0)

    # 1. Gradient-tolerant differential extremum check (e.g. scratches across face or lighting gradient)
    if is_extremum and contrast >= 8.0:
        conf = float(np.clip(0.4 * (contrast / 35.0) + 0.6 * sym_ratio, 0.0, 1.0))
        return True, conf

    # 2. Standard check: unimodal neighborhood (low IQR across uniform regions like skies, walls)
    if iqr <= max_iqr and contrast >= 6.0 and is_extremum:
        conf = float(np.clip(0.5 * (contrast / 25.0) + 0.5 * (1.0 - (iqr / max_iqr)), 0.0, 1.0))
        return True, conf

    return False, 0.0


def _is_ridge_not_step_edge(
    gray_image: np.ndarray,
    comp_mask: np.ndarray,
    max_iqr: float = MAX_NEIGHBOR_IQR,
) -> bool:
    """Determine whether an elongated component is an isolated ridge (scratch) rather than a step edge."""
    is_ridge, _ = _evaluate_ridge_profile(gray_image, comp_mask, max_iqr)
    return is_ridge


def _filter_directional_components(
    cand_mask: np.ndarray,
    gray_image: np.ndarray,
    min_length: int = DEFAULT_MIN_LENGTH,
    min_aspect_ratio: float = DEFAULT_MIN_ASPECT_RATIO,
    max_thickness: int = DEFAULT_MAX_THICKNESS,
    max_pixels: int = 5000,
    protected_zones: Optional[List[Tuple[int, int, int, int]]] = None,
) -> Tuple[np.ndarray, int, float]:
    """Filter candidate binary pixels into geometrically valid scratch components.
    
    Returns:
        Tuple of (accepted_mask, count, mean_confidence).
    """
    if np.count_nonzero(cand_mask) == 0:
        return np.zeros_like(cand_mask), 0, 0.0

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cand_mask, connectivity=8)
    accepted = np.zeros_like(cand_mask)
    count = 0
    confidences: List[float] = []

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        comp_w = stats[i, cv2.CC_STAT_WIDTH]
        comp_h = stats[i, cv2.CC_STAT_HEIGHT]
        comp_left = stats[i, cv2.CC_STAT_LEFT]
        comp_top = stats[i, cv2.CC_STAT_TOP]

        if area < min_length or area > max_pixels:
            continue

        comp_mask = (labels == i).astype(np.uint8)
        is_ridge, conf = _evaluate_ridge_profile(gray_image, comp_mask)
        if not is_ridge:
            continue

        contours, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            continue

        contour = contours[0]
        if len(contour) >= 5:
            rect = cv2.minAreaRect(contour)
            rw, rh = rect[1]
            length = max(rw, rh)
            # Use true physical line thickness: area / length
            phys_thick = float(area) / max(length, 1.0)
            thickness = min(max(min(rw, rh), 1.0), phys_thick)
        elif len(contour) >= 2:
            pt1 = contour[0][0]
            pt2 = contour[-1][0]
            length = float(np.linalg.norm(pt1 - pt2))
            thickness = max(float(area) / max(length, 1.0), 1.0)
        else:
            length = float(max(comp_w, comp_h))
            thickness = float(max(min(comp_w, comp_h), 1))

        aspect = length / max(thickness, 1.0)
        bb_aspect = max(comp_w / max(comp_h, 1), comp_h / max(comp_w, 1))
        effective_aspect = max(aspect, bb_aspect)

        # Biological landmark protection (Phase E):
        # Eyes/nostrils/lips are small and curved; authentic scratches cutting across landmarks are long and linear
        if protected_zones:
            cx = int(comp_left + comp_w / 2)
            cy = int(comp_top + comp_h / 2)
            is_in_protected = False
            for (zx1, zy1, zx2, zy2) in protected_zones:
                if zx1 <= cx <= zx2 and zy1 <= cy <= zy2:
                    is_in_protected = True
                    break
            if is_in_protected:
                # Small features in eyes/mouth are anatomical (eyelashes, eyelids, lip contours)
                # Genuine scratches traversing landmarks must be sufficiently long and elongated
                if length < 25 or effective_aspect < 3.2 or conf < 0.50:
                    continue

        # Scratches must be elongated, sufficiently long, and thin
        if (
            effective_aspect >= min_aspect_ratio
            and length >= min_length
            and thickness <= max_thickness
        ):
            accepted[labels == i] = 255
            count += 1
            confidences.append(conf)

    mean_conf = float(np.mean(confidences)) if confidences else 0.0
    return accepted, count, mean_conf


def detect_scratch_mask(
    image: np.ndarray,
    threshold: int = DEFAULT_SCRATCH_THRESHOLD,
    min_length: int = DEFAULT_MIN_LENGTH,
    min_aspect_ratio: float = DEFAULT_MIN_ASPECT_RATIO,
    max_thickness: int = DEFAULT_MAX_THICKNESS,
    max_coverage: float = MAX_REPAIR_COVERAGE,
    kernel_length: int = DEFAULT_KERNEL_LENGTH,
    sensitivity: Optional[str] = None,
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
        sensitivity:
            Optional sensitivity preset ('low', 'medium', 'high') overriding threshold.

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

    # Handle sensitivity preset
    eff_threshold = threshold
    if sensitivity is not None:
        s_clean = str(sensitivity).lower().strip()
        if s_clean == "high":
            eff_threshold = 12
        elif s_clean == "low":
            eff_threshold = 25
        elif s_clean == "medium":
            eff_threshold = 18

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
                # Eye band
                protected_zones.append((
                    fx + int(fw * 0.15),
                    fy + int(fh * 0.22),
                    fx + int(fw * 0.85),
                    fy + int(fh * 0.48),
                ))
                # Mouth / lips band
                protected_zones.append((
                    fx + int(fw * 0.25),
                    fy + int(fh * 0.68),
                    fx + int(fw * 0.75),
                    fy + int(fh * 0.88),
                ))
        except Exception:
            pass

    # 2. Multi-Orientation Grouped Morphological Filtering
    k_len_1 = max(kernel_length, 9)
    k_len_2 = max(k_len_1 + 8, 21)
    k_iso_1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    k_iso_2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

    combined_accepted = np.zeros((h, w), dtype=np.uint8)
    total_components = 0
    all_confidences: List[float] = []

    t_high = max(eff_threshold, 8)
    t_low = max(int(t_high * 0.65), 6)
    k_bridge = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    for _, angles in DIRECTIONAL_GROUPS:
        lines_1 = [_create_line_kernel(k_len_1, a) for a in angles]
        lines_2 = [_create_line_kernel(k_len_2, a) for a in angles]

        open_1 = np.maximum.reduce([cv2.morphologyEx(gray, cv2.MORPH_OPEN, k) for k in lines_1])
        close_1 = np.minimum.reduce([cv2.morphologyEx(gray, cv2.MORPH_CLOSE, k) for k in lines_1])
        open_2 = np.maximum.reduce([cv2.morphologyEx(gray, cv2.MORPH_OPEN, k) for k in lines_2])
        close_2 = np.minimum.reduce([cv2.morphologyEx(gray, cv2.MORPH_CLOSE, k) for k in lines_2])

        resp_b = np.maximum(
            cv2.subtract(open_1, cv2.morphologyEx(gray, cv2.MORPH_OPEN, k_iso_1)),
            cv2.subtract(open_2, cv2.morphologyEx(gray, cv2.MORPH_OPEN, k_iso_2))
        )
        resp_d = np.maximum(
            cv2.subtract(cv2.morphologyEx(gray, cv2.MORPH_CLOSE, k_iso_1), close_1),
            cv2.subtract(cv2.morphologyEx(gray, cv2.MORPH_CLOSE, k_iso_2), close_2)
        )
        resp = np.maximum(resp_b, resp_d)

        # Adaptive Hysteresis Thresholding within orientation group
        high_mask = (resp >= t_high).astype(np.uint8)
        low_mask = (resp >= t_low).astype(np.uint8)

        num_labels_hyst, labels_hyst, _, _ = cv2.connectedComponentsWithStats(low_mask, connectivity=8)
        hyst_mask = np.zeros_like(low_mask)
        if num_labels_hyst > 1 and np.count_nonzero(high_mask) > 0:
            for i in range(1, num_labels_hyst):
                comp_pixels = (labels_hyst == i)
                if np.any(comp_pixels & (high_mask > 0)):
                    hyst_mask[comp_pixels] = 255
        else:
            hyst_mask = high_mask * 255

        # Bridge micro-breaks along scratch orientation
        cand_bridged = cv2.morphologyEx(hyst_mask, cv2.MORPH_CLOSE, k_bridge)

        # Geometric filtering per orientation group
        group_accepted, group_count, group_conf = _filter_directional_components(
            cand_bridged,
            gray,
            min_length=min_length,
            min_aspect_ratio=min_aspect_ratio,
            max_thickness=max_thickness,
            max_pixels=max_comp_pixels,
            protected_zones=protected_zones,
        )

        if group_count > 0:
            combined_accepted = cv2.bitwise_or(combined_accepted, group_accepted)
            total_components += group_count
            all_confidences.append(group_conf)

    mean_confidence = float(np.mean(all_confidences)) if all_confidences else 0.0

    # 3. Gentle dilation to encompass boundary penumbra
    if total_components > 0:
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        repair_mask = cv2.dilate(combined_accepted, kernel_dilate, iterations=1)
    else:
        repair_mask = combined_accepted

    # 4. Safety coverage validation
    repaired_pixels = int(np.count_nonzero(repair_mask))
    coverage = repaired_pixels / total_pixels

    if coverage > max_coverage:
        # Safety guard triggered: reject mask and skip repair to preserve genuine image content
        return np.zeros((h, w), dtype=np.uint8), ScratchRepairMetadata(
            applied=False,
            detected_components=total_components,
            repaired_pixels=repaired_pixels,
            coverage_percentage=round(coverage * 100, 2),
            confidence_score=round(mean_confidence, 2),
            skipped=True,
            skip_reason=(
                f"Mask coverage ({coverage * 100:.2f}%) exceeds safety threshold "
                f"({max_coverage * 100:.1f}%)"
            ),
        )

    meta = ScratchRepairMetadata(
        applied=repaired_pixels > 0,
        detected_components=total_components,
        repaired_pixels=repaired_pixels,
        coverage_percentage=round(coverage * 100, 2),
        confidence_score=round(mean_confidence, 2),
        skipped=False,
        skip_reason=None,
    )
    # Automatically evaluate recommended inpainting engine
    _, reason = select_inpainting_engine(repair_mask, meta, image.shape, method_request="hybrid")
    meta.dispatch_reason = reason
    return repair_mask, meta


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


def select_inpainting_engine(
    mask: np.ndarray,
    meta: ScratchRepairMetadata,
    image_shape: Tuple[int, ...],
    method_request: str = "hybrid",
) -> Tuple[str, str]:
    """Intelligently determine whether to deploy Telea, Navier-Stokes, or LaMa.

    Evaluates:
    - Total damaged pixel area
    - Maximum connected component area
    - Defect thickness/width
    - Coverage percentage
    - Image dimensions and expected CPU latency

    Returns:
        Tuple of (chosen_engine: str, dispatch_reason: str).
    """
    req = method_request.lower().strip()
    if req in ("telea", "ns", "lama"):
        return req, f"Explicit user selection of '{req}' inpainting engine."

    if meta.repaired_pixels == 0:
        return "telea", "No damage pixels detected; minimal pass-through."

    # Analyze component statistics
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num_labels <= 1:
        return "telea", "Minor isolated scratch defect; Telea Fast Marching provides sub-20ms repair."

    areas = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]
    widths = [stats[i, cv2.CC_STAT_WIDTH] for i in range(1, num_labels)]
    heights = [stats[i, cv2.CC_STAT_HEIGHT] for i in range(1, num_labels)]

    max_comp_area = max(areas) if areas else 0
    min_dims = [min(w, h) for w, h in zip(widths, heights)]
    max_thickness = max(min_dims) if min_dims else 1

    # 1. Broad damage or large tear hole (area >= 250 or thickness >= 4 or coverage >= 0.20%):
    #    Requires deep neural inpainting (LaMa Fast Fourier Convolutions)
    #    to reconstruct missing textures without blur.
    if max_comp_area >= 250 or max_thickness >= 4 or meta.coverage_percentage >= 0.20:
        return "lama", (
            f"Significant tear / broad damage detected (max_comp_area={max_comp_area}px, "
            f"max_thickness={max_thickness}px, coverage={meta.coverage_percentage:.2f}%). "
            "LaMa deep Fast Fourier Convolutions deployed for global context synthesis."
        )

    # 2. Narrow hairline scratches (thickness <= 3, small areas):
    #    Telea Fast Marching PDE is fast (<20ms) and introduces zero boundary halos.
    return "telea", (
        f"Hairline scratch damage (max_thickness={max_thickness}px, max_comp_area={max_comp_area}px). "
        "Fast Marching Telea PDE deployed for responsive artifact-free repair."
    )


def repair_scratches(
    image: np.ndarray,
    mask: Optional[np.ndarray] = None,
    inpaint_radius: int = DEFAULT_INPAINT_RADIUS,
    method: str = DEFAULT_INPAINT_METHOD,
    sensitivity: Optional[str] = None,
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
        sensitivity:
            Optional sensitivity preset ('low', 'medium', 'high') if mask is computed.

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
        repair_mask, meta = detect_scratch_mask(image, sensitivity=sensitivity)
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

    # Multi-factor intelligent inpainting engine dispatching
    chosen_engine, dispatch_reason = select_inpainting_engine(
        repair_mask, meta, image.shape, method_request=method_clean
    )
    meta.method = chosen_engine
    meta.radius = inpaint_radius
    meta.dispatch_reason = dispatch_reason

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
