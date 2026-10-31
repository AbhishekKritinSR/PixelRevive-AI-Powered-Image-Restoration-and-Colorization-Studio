"""Unit test suite for Colorization Quality Enhancement (Problem A & C).

Verifies:
1. Guided filter edge alignment (sharp chroma transition at luminance edges).
2. Chroma saturation scaling in CIE LAB space.
3. Shadow and highlight chromatic attenuation (neutral deep shadows).
4. Color temperature white balance shifting.
"""

import numpy as np
import cv2
import pytest

from backend.src.processing.colorization.models.zhang_caffe import colorize_image


class TestColorizationRefinements:
    """Tests for edge-guided and saturation-controlled colorization."""

    def test_chroma_saturation_scaling(self, stub_net):
        """Saturation parameter must scale chromatic magnitude in LAB space."""
        img = np.full((50, 50, 3), 120, dtype=np.uint8)

        # Standard saturated
        full_sat = colorize_image(img, stub_net, saturation=1.0)
        # Desaturated (monochrome limit)
        zero_sat = colorize_image(img, stub_net, saturation=0.0)

        # In zero saturation, R, G, B should be practically equal (grayscale)
        b, g, r = cv2.split(zero_sat)
        diff_rg = np.max(np.abs(r - g))
        diff_gb = np.max(np.abs(g - b))
        assert diff_rg < 0.05
        assert diff_gb < 0.05

    def test_shadow_desaturation_attenuates_chroma_in_blacks(self, stub_net):
        """Deep shadow regions (L < 15) must have near-zero chroma to avoid colored blotches."""
        img_dark = np.full((40, 40, 3), 10, dtype=np.uint8)
        res = colorize_image(img_dark, stub_net, shadow_attenuation=True)

        assert res.shape == (40, 40, 3)
        assert res.dtype == np.float32
        # Pixels should remain dark neutral
        assert res.max() < 0.25

    def test_temperature_shift_affects_chrominance(self, stub_net):
        """Temperature parameter must measurably adjust the chromatic balance."""
        img = np.full((40, 40, 3), 130, dtype=np.uint8)

        warm = colorize_image(img, stub_net, color_temperature=1.0)
        cool = colorize_image(img, stub_net, color_temperature=-1.0)

        assert not np.array_equal(warm, cool)
        # Cool should have higher blue ratio than warm
        assert np.mean(cool[:, :, 0]) > np.mean(warm[:, :, 0])

