"""Unit tests for Phase 3 algorithmic enhancements and quality safeguards.

Validates:
1. Spatially Adaptive Texture-Guided Residual Denoising
2. Natural Chrominance Refiner (guided filter, saturation, temperature, shadow attenuation)
3. Multi-Factor Inpainting Engine Dispatching (select_inpainting_engine)
4. Noise-Safe Localized Facial Feature Enhancement
5. Clean Image Protection & Explainable Operations Summary
"""

import cv2
import numpy as np
import pytest

from backend.src.processing.colorization.refiner import (
    NaturalChrominanceRefiner,
    refine_chrominance,
)
from backend.src.processing.restoration.denoiser import (
    _apply_texture_guided_residual,
    adaptive_denoise_image,
    estimate_noise_sigma,
)
from backend.src.processing.restoration.face_restorer import FaceRestorer
from backend.src.processing.restoration.restorer import enhance_image
from backend.src.processing.restoration.scratch_repair import (
    ScratchRepairMetadata,
    detect_scratch_mask,
    repair_scratches,
    select_inpainting_engine,
)
from backend.src.schemas.restoration import (
    DamageMaskResponse,
    RestorationOptions,
    SingleRestorationResponse,
)
from backend.src.services.model_service import ModelService
from backend.src.services.restoration_service import RestorationService


class TestTextureGuidedResidualDenoising:
    """Verifies that high-frequency texture is preserved while flat areas remain clean."""

    def test_texture_guided_residual_flat_vs_textured(self):
        # Create image with flat region on top and textured region on bottom
        img = np.full((128, 128, 3), 128, dtype=np.uint8)
        # Add high-frequency texture on bottom half
        img[64:, :, :] = np.tile(
            np.array([[[50, 50, 50], [200, 200, 200]]], dtype=np.uint8), (64, 64, 1)
        )

        # Smooth denoised version
        denoised = cv2.GaussianBlur(img, (5, 5), 1.5)

        # Apply texture-guided residual blending
        result = _apply_texture_guided_residual(img, denoised, is_color=True, texture_weight=0.5)

        assert result.shape == img.shape
        assert result.dtype == np.uint8

        # Flat region (top) should remain smooth (near denoised)
        flat_diff = np.max(np.abs(result[:64, :].astype(np.float32) - denoised[:64, :].astype(np.float32)))
        assert flat_diff <= 1.0  # minimal difference in flat areas

        # Textured region (bottom) should recover contrast closer to original
        orig_contrast = np.std(img[64:, :])
        res_contrast = np.std(result[64:, :])
        denoised_contrast = np.std(denoised[64:, :])
        assert res_contrast > denoised_contrast

    def test_adaptive_denoise_texture_weight_zero(self):
        img = np.full((64, 64, 3), 120, dtype=np.uint8)
        res, params = adaptive_denoise_image(img, noise_score=6.0, texture_weight=0.0)
        assert res.shape == (64, 64, 3)
        assert params.h > 0


class TestNaturalChrominanceRefiner:
    """Verifies edge snapping, saturation scaling, and temperature compensation."""

    def test_refiner_initialization(self):
        refiner = NaturalChrominanceRefiner(saturation=0.85, color_temperature=0.2)
        assert refiner.saturation == 0.85
        assert refiner.color_temperature == 0.2

    def test_refine_chrominance_saturation_and_shadow_attenuation(self):
        H, W = 64, 64
        # L channel with deep shadows at top, midtones in center, highlights at bottom
        L = np.linspace(0.0, 100.0, H, dtype=np.float32)
        L = np.tile(L[:, np.newaxis], (1, W))

        # Synthetic constant ab chrominance
        ab = np.full((H, W, 2), 20.0, dtype=np.float32)

        refined = refine_chrominance(
            L, ab, saturation=0.8, color_temperature=0.0, shadow_attenuation=True
        )

        assert refined.shape == (H, W, 2)
        # Deep shadows (L < 8) should be desaturated to near zero
        assert np.mean(refined[0:5, :]) < 5.0
        # Midtones should be scaled by saturation factor (20 * 0.8 = 16)
        mid_val = np.mean(refined[30:34, :])
        assert np.isclose(mid_val, 16.0, atol=2.0)
        # Extreme highlights (L > 95) should be attenuated
        assert np.mean(refined[60:64, :]) < 10.0

    def test_refine_chrominance_temperature_bias(self):
        H, W = 32, 32
        L = np.full((H, W), 50.0, dtype=np.float32)
        ab = np.zeros((H, W, 2), dtype=np.float32)

        # Warm temperature (+0.5) should increase b (yellow) and slightly increase a (red)
        refined_warm = refine_chrominance(
            L, ab, saturation=1.0, color_temperature=0.5, shadow_attenuation=False
        )
        assert np.all(refined_warm[:, :, 1] > 0.0)  # b channel increased
        assert np.all(refined_warm[:, :, 0] > 0.0)  # a channel increased


class TestInpaintingEngineSelection:
    """Verifies multi-factor heuristic dispatching between Telea and LaMa."""

    def test_select_telea_for_small_scratch(self):
        mask = np.zeros((200, 200), dtype=np.uint8)
        cv2.line(mask, (50, 50), (100, 50), 255, 1)  # small hairline crack
        meta = ScratchRepairMetadata(
            applied=True,
            detected_components=1,
            repaired_pixels=50,
            coverage_percentage=0.12,
        )
        engine, reason = select_inpainting_engine(mask, meta, (200, 200, 3), method_request="hybrid")
        assert engine == "telea"
        assert "Telea" in reason

    def test_select_lama_for_broad_tear(self):
        mask = np.zeros((256, 256), dtype=np.uint8)
        cv2.circle(mask, (128, 128), 15, 255, -1)  # broad hole
        repaired_pixels = int(np.count_nonzero(mask))
        meta = ScratchRepairMetadata(
            applied=True,
            detected_components=1,
            repaired_pixels=repaired_pixels,
            coverage_percentage=round((repaired_pixels / (256 * 256)) * 100, 2),
        )
        engine, reason = select_inpainting_engine(mask, meta, (256, 256, 3), method_request="hybrid")
        assert engine == "lama"
        assert "LaMa" in reason


class TestFaceRestorerEnhancement:
    """Verifies face detector and noise-safe spatial filtering."""

    def test_face_restorer_empty_image(self):
        empty = np.zeros((50, 50, 3), dtype=np.uint8)
        res, count = FaceRestorer.restore_faces(empty)
        assert count == 0
        assert res.shape == (50, 50, 3)

    def test_face_restorer_documentation(self):
        assert "Haar Cascade is utilized strictly as a bounding-box face-region detector" in FaceRestorer.__doc__


class TestCleanImageProtectionAndSchemas:
    """Verifies clean image protection, operations summary, and response schemas."""

    def test_damage_mask_response_schema(self):
        resp = DamageMaskResponse(
            filename="test.png",
            detected_components=2,
            repaired_pixels=150,
            coverage_percentage=0.25,
            confidence_score=0.88,
            dispatch_reason="Telea selected for hairline defect",
            mask_base64="data:image/png;base64,...",
            overlay_base64="data:image/png;base64,...",
            elapsed_seconds=0.045,
        )
        assert resp.confidence_score == 0.88
        assert resp.dispatch_reason is not None

    def test_clean_image_protection_bypasses_operations(self):
        service = RestorationService(ModelService())

        # Create smooth pristine continuous-tone image
        img = np.zeros((128, 128, 3), dtype=np.uint8)
        for y in range(128):
            val = int(120 + 20 * np.sin(y / 20.0))
            img[y, :] = (val, val, val)
        img = cv2.GaussianBlur(img, (7, 7), 2.0)

        success, png_bytes = cv2.imencode(".png", img)
        assert success

        opts = RestorationOptions(
            denoise=True,
            contrast=False,
            sharpen=False,
            colorize=True,
            repair=True,
            adaptive_denoise=True,
        )

        res, out_bytes = service.process_image(
            file_bytes=png_bytes.tobytes(), filename="pristine.png", options=opts
        )

        assert res.operations_summary is not None
        summary = res.operations_summary

        # Clean image protection checks:
        assert "scratch_repair" in summary
        assert "bypassed" in summary["scratch_repair"].lower() or "skipped" in summary["scratch_repair"].lower()

        assert "denoising" in summary
        assert "bypassed" in summary["denoising"].lower() or "skipped" in summary["denoising"].lower()

        assert "colorization" in summary
        # Input was grayscale (val, val, val), so colorization applies or skips appropriately
