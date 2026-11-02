"""Module: face_restorer.py

Purpose:
Provides identity-preserving facial feature restoration and localized portrait enhancement.
Preserves true anatomical facial identity, eye shape, nose, and mouth structure while
clarifying degraded historical portrait features without artificial plastic beautification.

Responsibilities:
- Detect facial regions using OpenCV Haar Cascade or DNN face detector.
- Extract localized facial region of interest (ROI) with soft boundary margins.
- Apply localized bilateral detail recovery, CLAHE micro-contrast, and unsharp masking.
- Blend enhanced facial features back into the portrait using feathered elliptical alpha masks.
- Ensure strict identity preservation without altering facial geometry.

Syllabus Alignment:
- VIT BCSE403L Module 5: Image Segmentation - Region-based face detection and localized masking.
- VIT BCSE403L Module 2: Spatial Filtering - Localized CLAHE contrast enhancement and unsharp masking.
"""

from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

try:
    from src.config import MODEL_DIR
    FACE_CASCADE_PATH = MODEL_DIR / "haarcascade_frontalface_default.xml"
except ImportError:
    FACE_CASCADE_PATH = Path("model") / "haarcascade_frontalface_default.xml"


class FaceRestorer:
    """Provides localized, identity-preserving facial restoration for historical portraits.

    Methodological Note:
        Haar Cascade is utilized strictly as a bounding-box face-region detector
        (not a facial landmark regressor or generative reconstructor). Facial
        enhancement is performed via deterministic, noise-safe localized spatial
        domain filtering (CLAHE micro-contrast and unsharp masking in CIELAB space)
        blended via feathered elliptical alpha masks. This strictly preserves genuine
        historical facial identity without hallucinating synthetic facial structures
        or causing plastic artifacts.
    """

    _cascade: Optional[cv2.CascadeClassifier] = None

    @classmethod
    def get_cascade(cls, cascade_path: Optional[Path] = None) -> Optional[cv2.CascadeClassifier]:
        """Lazy load and cache the Haar Cascade face detector."""
        if cls._cascade is None:
            path = cascade_path or FACE_CASCADE_PATH
            if not path.is_file():
                alt_path = Path("model") / "haarcascade_frontalface_default.xml"
                if alt_path.is_file():
                    path = alt_path
            if path.is_file():
                cls._cascade = cv2.CascadeClassifier(str(path))
            elif hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
                cv2_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
                if cv2_path.is_file():
                    cls._cascade = cv2.CascadeClassifier(str(cv2_path))
        return cls._cascade

    @classmethod
    def detect_faces(cls, image_bgr: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect face bounding boxes (x, y, w, h) in a BGR image.

        Uses calibrated multi-scale Haar cascade detection with image-scale-proportional
        minimum window sizing to suppress false positive spikes on film grain while
        supporting an adaptive CLAHE fallback for severely faded archival photographs.
        """
        cascade = cls.get_cascade()
        if cascade is None or cascade.empty():
            return []

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        img_h, img_w = gray.shape[:2]

        # Dynamic scale-proportional minimum face dimension to reject tiny grain patches
        min_dim = max(32, min(img_h, img_w) // 25)

        # Primary pass: raw grayscale detection with robust neighbor grouping
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(min_dim, min_dim),
        )

        # Fallback pass: localized CLAHE enhancement for severely faded daguerreotypes
        if len(faces) == 0:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            contrasted = clahe.apply(gray)
            faces = cascade.detectMultiScale(
                contrasted,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(min_dim, min_dim),
            )

        return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]

    @classmethod
    def restore_faces(
        cls,
        image_bgr: np.ndarray,
        enhancement_strength: float = 0.75,
    ) -> Tuple[np.ndarray, int]:
        """Apply localized identity-preserving detail restoration to detected faces.

        Args:
            image_bgr:
                Input image as uint8 NumPy array of shape (H, W, 3).
            enhancement_strength:
                Strength coefficient between 0.0 and 1.0 (default 0.75).

        Returns:
            Tuple of (restored BGR image, count of faces enhanced).
        """
        if not isinstance(image_bgr, np.ndarray) or image_bgr.ndim != 3:
            return image_bgr, 0

        faces = cls.detect_faces(image_bgr)
        if not faces or enhancement_strength <= 0.0:
            return image_bgr.copy(), len(faces)

        output = image_bgr.copy()
        img_h, img_w = image_bgr.shape[:2]

        for (x, y, w, h) in faces:
            # Expand bounding box (15% margin) to capture facial contours smoothly
            margin_x = int(w * 0.15)
            margin_y = int(h * 0.15)
            x1 = max(0, x - margin_x)
            y1 = max(0, y - margin_y)
            x2 = min(img_w, x + w + margin_x)
            y2 = min(img_h, y + h + margin_y)

            roi_h = y2 - y1
            roi_w = x2 - x1
            if roi_h < 10 or roi_w < 10:
                continue

            roi = image_bgr[y1:y2, x1:x2]

            # 1. Transform ROI to LAB color space to operate on luminance L
            roi_lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
            L, A, B = cv2.split(roi_lab)

            # 2. Localized adaptive contrast enhancement on face (CLAHE)
            clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(4, 4))
            L_enhanced = clahe.apply(L)

            # 3. High-definition unsharp masking to recover fine facial contours
            L_blur = cv2.GaussianBlur(L_enhanced, (0, 0), sigmaX=1.5)
            L_sharp = cv2.addWeighted(L_enhanced, 1.8, L_blur, -0.8, 0)
            L_sharp = np.clip(L_sharp, 0, 255).astype(np.uint8)

            # Recombine with original chroma to guarantee zero color alteration
            enhanced_roi_lab = cv2.merge([L_sharp, A, B])
            enhanced_roi = cv2.cvtColor(enhanced_roi_lab, cv2.COLOR_LAB2BGR)

            # 4. Elliptical feather mask to eliminate rectangular boundary artifacts
            center = (roi_w // 2, roi_h // 2)
            axes = (int(roi_w * 0.44), int(roi_h * 0.46))
            mask = np.zeros((roi_h, roi_w), dtype=np.float32)
            cv2.ellipse(mask, center, axes, 0, 0, 360, 1.0, -1)
            # Smooth mask edge with Gaussian filter for seamless boundary transition
            k_blur = max(5, (min(roi_h, roi_w) // 8) | 1)
            mask = cv2.GaussianBlur(mask, (k_blur, k_blur), 0)
            mask = np.clip(mask * float(enhancement_strength), 0.0, 1.0)
            mask_3c = mask[:, :, np.newaxis]

            # 5. Alpha blend enhanced ROI into output canvas
            output[y1:y2, x1:x2] = np.clip(
                enhanced_roi.astype(np.float32) * mask_3c + roi.astype(np.float32) * (1.0 - mask_3c),
                0,
                255,
            ).astype(np.uint8)

        return output, len(faces)

        return output, len(faces)
