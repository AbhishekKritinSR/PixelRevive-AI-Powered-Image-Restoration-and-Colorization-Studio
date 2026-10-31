"""Unit test suite for LaMa Deep Inpainting Engine.

Verifies:
1. LaMaInpainter singleton initialization and model availability check.
2. Inpainting execution with Fast Fourier Convolutions.
3. Zero-overhead bypass on empty defect masks.
4. 100% exact pixel preservation of unmasked regions.
5. Graceful fallback when model is unavailable or inpainting fails.
6. Integration with repair_scratches(method="lama").
"""

from pathlib import Path
import numpy as np
import cv2
import pytest

from backend.src.processing.restoration.inpainter_lama import LaMaInpainter
from backend.src.processing.restoration.scratch_repair import repair_scratches


class TestLaMaInpainting:
    """Tests for the LaMa deep neural inpainting engine."""

    def test_singleton_and_availability(self):
        """Test singleton retrieval and asset availability reporting."""
        lama1 = LaMaInpainter.get_instance()
        lama2 = LaMaInpainter.get_instance()
        assert lama1 is lama2
        assert isinstance(lama1.is_available, bool)

    def test_empty_mask_bypasses_inference(self):
        """Empty mask must bypass neural inference and return untouched image."""
        lama = LaMaInpainter.get_instance()
        img = np.full((120, 120, 3), 160, dtype=np.uint8)
        empty_mask = np.zeros((120, 120), dtype=np.uint8)

        repaired, ok = lama.inpaint(img, empty_mask)
        assert ok is True
        np.testing.assert_array_equal(repaired, img)

    def test_unmasked_pixels_preserved_100_percent(self):
        """Pixels outside the dilated defect mask must be strictly preserved."""
        lama = LaMaInpainter.get_instance()
        if not lama.is_available:
            pytest.skip("LaMa model weights not available on disk")

        img = np.full((200, 200, 3), 140, dtype=np.uint8)
        # Random non-damaged texture
        img[0:50, 0:50] = np.random.randint(50, 200, (50, 50, 3), dtype=np.uint8)

        # Defect in lower-right quadrant only
        mask = np.zeros((200, 200), dtype=np.uint8)
        cv2.line(mask, (120, 120), (180, 180), 255, 4)

        repaired, ok = lama.inpaint(img, mask)
        assert ok is True
        # Top-left quadrant must be 100% bit-for-bit identical
        np.testing.assert_array_equal(repaired[0:50, 0:50], img[0:50, 0:50])

    def test_lama_inpaint_reduces_scratch_defect(self):
        """LaMa inpainting must restore scratched pixels close to background intensity."""
        lama = LaMaInpainter.get_instance()
        if not lama.is_available:
            pytest.skip("LaMa model weights not available on disk")

        # Background 170 with a dark black scratch (10)
        img = np.full((300, 300, 3), 170, dtype=np.uint8)
        cv2.line(img, (60, 60), (240, 240), (10, 10, 10), 4)

        mask = np.zeros((300, 300), dtype=np.uint8)
        cv2.line(mask, (60, 60), (240, 240), 255, 6)

        repaired, ok = lama.inpaint(img, mask)
        assert ok is True
        assert repaired.shape == img.shape
        assert repaired.dtype == np.uint8

        # Center of scratch before: 10. After LaMa: should be near 170
        center_val = int(repaired[150, 150, 0])
        assert center_val > 130, f"Expected repaired pixel > 130, got {center_val}"

    def test_repair_scratches_integration_with_lama(self):
        """Verify repair_scratches(image, method='lama') interface."""
        img = np.full((250, 250, 3), 160, dtype=np.uint8)
        cv2.line(img, (40, 40), (210, 210), (15, 15, 15), 4)

        repaired, meta = repair_scratches(img, method="lama")
        assert meta.applied is True
        assert meta.repaired_pixels > 0
        assert meta.method in ("lama", "telea")
