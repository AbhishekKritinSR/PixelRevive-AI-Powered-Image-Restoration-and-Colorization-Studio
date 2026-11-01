"""Module: inpainter_lama.py

Purpose:
Provides high-fidelity deep neural inpainting using the LaMa (Large Mask Inpainting)
architecture (Suvorov et al., WACV 2022) with Fast Fourier Convolutions (FFC).
Executes via ONNX Runtime on CPU or CUDA.

Responsibilities:
- Validate model asset presence on disk (model/lama_fp32.onnx).
- Manage thread-safe ONNX Runtime InferenceSession lifecycle.
- Preprocess arbitrary-dimension input images and binary masks into 512x512 tensors.
- Resample masks with anti-aliasing preservation to prevent dropping thin scratches.
- Execute deep neural inference with Fast Fourier Convolutions.
- Postprocess and seamlessly blend inpainted regions back into original resolution.
- Eliminate boundary step discontinuities via distance-transform feathering.
- Ensure 100% bit-for-bit preservation of undamaged pixels outside the defect mask.
- Provide graceful fallback when the model asset is unavailable.

Syllabus Alignment:
- VIT BCSE403L Module 4: Image Restoration - Degradation models and image reconstruction.
- VIT BCSE403L Module 3: Image Transforms and Frequency Domain Processing (Fourier domain convolutions).
"""

from pathlib import Path
import threading
from typing import Optional, Tuple

import cv2
import numpy as np

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

from backend.src.core.config import settings

LAMA_MODEL_PATH = Path("model") / "lama_fp32.onnx"


class LaMaInpainter:
    """Thread-safe singleton adapter for the LaMa deep inpainting network."""

    _instance: Optional["LaMaInpainter"] = None
    _lock = threading.Lock()

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or LAMA_MODEL_PATH
        self._session: Optional[ort.InferenceSession] = None
        self._init_lock = threading.Lock()

    @classmethod
    def get_instance(cls, model_path: Optional[Path] = None) -> "LaMaInpainter":
        """Obtain or initialize the thread-safe singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(model_path)
        return cls._instance

    @property
    def is_available(self) -> bool:
        """Check whether ONNX Runtime is installed and model weights exist on disk."""
        return HAS_ONNX and self.model_path.is_file()

    @property
    def is_loaded(self) -> bool:
        """Check whether the inference session is active in memory."""
        return self._session is not None

    def load_model(self) -> bool:
        """Load the ONNX model into memory using CPU execution provider."""
        if not self.is_available:
            return False

        if not self.is_loaded:
            with self._init_lock:
                if not self.is_loaded:
                    opts = ort.SessionOptions()
                    opts.intra_op_num_threads = 4
                    opts.inter_op_num_threads = 2
                    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

                    providers = ["CPUExecutionProvider"]
                    if HAS_ONNX and "CUDAExecutionProvider" in ort.get_available_providers():
                        providers.insert(0, "CUDAExecutionProvider")

                    self._session = ort.InferenceSession(
                        str(self.model_path),
                        sess_options=opts,
                        providers=providers,
                    )
        return True

    def inpaint(
        self,
        image_bgr: np.ndarray,
        mask: np.ndarray,
    ) -> Tuple[np.ndarray, bool]:
        """Inpaint scratch or damaged regions marked in the binary mask.

        Args:
            image_bgr:
                Input image as uint8 NumPy array of shape (H, W, 3).
            mask:
                Binary repair mask as uint8 NumPy array of shape (H, W) where >0 marks defects.

        Returns:
            Tuple of (inpainted BGR uint8 image, boolean success flag).
            If model is unavailable or mask is empty, returns original image and False/True.
        """
        if not isinstance(image_bgr, np.ndarray) or not isinstance(mask, np.ndarray):
            raise TypeError("Image and mask must be numpy ndarrays")

        h, w = image_bgr.shape[:2]

        # Fast path: empty mask requires zero inpainting
        if np.count_nonzero(mask) == 0:
            return image_bgr.copy(), True

        if not self.is_available:
            return image_bgr.copy(), False

        if not self.is_loaded:
            if not self.load_model():
                return image_bgr.copy(), False

        # Dilate mask slightly to guarantee coverage of anti-aliased scratch edges
        k3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask_dilated = cv2.dilate(mask, k3, iterations=1)

        # Preprocess input: BGR uint8 -> RGB float32 [0.0, 1.0]
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        rgb_512 = cv2.resize(rgb, (512, 512), interpolation=cv2.INTER_LINEAR)

        # Preprocess mask: uint8 -> float32 [0.0, 1.0] (1.0 = defect to repair)
        # Resample with INTER_LINEAR to prevent thin 1-2px scratches from aliasing out
        mask_binary = (mask_dilated > 0).astype(np.float32)
        mask_512 = (cv2.resize(mask_binary, (512, 512), interpolation=cv2.INTER_LINEAR) > 0.02).astype(np.float32)

        # Zero-out defect pixels in input tensor (standard LaMa protocol)
        rgb_512 = rgb_512 * (1.0 - mask_512[:, :, np.newaxis])

        # Format tensors: (1, 3, 512, 512) and (1, 1, 512, 512)
        input_img = np.transpose(rgb_512, (2, 0, 1))[np.newaxis, ...]
        input_mask = mask_512[np.newaxis, np.newaxis, ...]

        try:
            raw_out = self._session.run(
                ["output"],
                {"image": input_img, "mask": input_mask},
            )[0]
        except Exception:
            return image_bgr.copy(), False

        # Shape: (1, 3, 512, 512) -> (512, 512, 3)
        out_patch = np.transpose(raw_out[0], (1, 2, 0))

        # Handle value range: LaMa ONNX directly outputs values in [0, 255]
        if out_patch.max() <= 1.05:
            out_patch = out_patch * 255.0
        out_patch = np.clip(out_patch, 0, 255).astype(np.uint8)

        # Convert back to BGR and restore original resolution
        repaired_bgr_512 = cv2.cvtColor(out_patch, cv2.COLOR_RGB2BGR)
        repaired_bgr = cv2.resize(repaired_bgr_512, (w, h), interpolation=cv2.INTER_LINEAR)

        # Seamless boundary feathering & strict uncorrupted pixel preservation guard:
        # Use distance transform to create a smooth 2-pixel transition ramp at mask edges,
        # completely preventing step-edge ringing when Laplacian sharpening runs later.
        dist = cv2.distanceTransform((mask_dilated > 0).astype(np.uint8), cv2.DIST_L2, 3)
        alpha = np.clip(dist / 2.0, 0.0, 1.0)[:, :, np.newaxis]
        blended = (repaired_bgr.astype(np.float32) * alpha + image_bgr.astype(np.float32) * (1.0 - alpha))
        result = np.clip(blended, 0, 255).astype(np.uint8)

        # Hard safety guarantee: outside mask_dilated, 100% bit-for-bit identical to image_bgr
        result[mask_dilated == 0] = image_bgr[mask_dilated == 0]

        return result, True
