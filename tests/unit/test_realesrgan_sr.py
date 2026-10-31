"""Unit test suite for Real-ESRGAN Super-Resolution Engine.

Verifies:
1. RealESRGANUpscaler singleton retrieval and asset availability.
2. 4x and 2x upscaling on synthetic RGB images.
3. Shape, dtype, and finite value integrity.
4. Integration with upscale_image(scale=4, model="realesrgan").
"""

import numpy as np
import pytest

from backend.src.processing.restoration.sr_realesrgan import RealESRGANUpscaler
from backend.src.processing.restoration.super_resolution import upscale_image


class TestRealESRGAN:
    """Tests for Real-ESRGAN AI super-resolution."""

    def test_singleton_and_availability(self):
        """Test singleton retrieval and weights check."""
        sr1 = RealESRGANUpscaler.get_instance()
        sr2 = RealESRGANUpscaler.get_instance()
        assert sr1 is sr2
        assert isinstance(sr1.is_available, bool)

    def test_realesrgan_4x_upscaling(self):
        """Test native 4x upscaling."""
        sr = RealESRGANUpscaler.get_instance()
        if not sr.is_available:
            pytest.skip("Real-ESRGAN weights not available on disk")

        img = np.full((32, 40, 3), 120, dtype=np.uint8)
        upscaled, ok = sr.upscale(img, target_scale=4)

        assert ok is True
        assert upscaled.shape == (32 * 4, 40 * 4, 3)
        assert upscaled.dtype == np.uint8
        assert np.all(np.isfinite(upscaled))

    def test_realesrgan_2x_upscaling(self):
        """Test 2x upscaling with Lanczos downsampling."""
        sr = RealESRGANUpscaler.get_instance()
        if not sr.is_available:
            pytest.skip("Real-ESRGAN weights not available on disk")

        img = np.full((32, 40, 3), 120, dtype=np.uint8)
        upscaled, ok = sr.upscale(img, target_scale=2)

        assert ok is True
        assert upscaled.shape == (32 * 2, 40 * 2, 3)
        assert upscaled.dtype == np.uint8

    def test_upscale_image_integration(self):
        """Test integration via upscale_image(..., model='realesrgan')."""
        img = np.full((30, 30, 3), 110, dtype=np.uint8)
        upscaled, meta = upscale_image(img, scale=4, model="realesrgan")

        assert meta.applied is True
        assert meta.scale == 4
        assert meta.model_name in ("realesrgan_x4", "fsrcnn_x4")
        assert upscaled.shape == (120, 120, 3)
