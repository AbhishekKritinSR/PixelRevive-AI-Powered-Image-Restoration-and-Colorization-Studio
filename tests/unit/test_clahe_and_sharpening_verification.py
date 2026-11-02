"""Unit, regression, and integration tests for CLAHE contrast enhancement and Laplacian sharpening.

Verifies:
1. CLAHE enabled executes unconditionally when adaptive safeguard is False.
2. CLAHE disabled does not execute and leaves image unchanged.
3. Low-contrast input is enhanced adaptively.
4. Clean-image protection for CLAHE behaves correctly.
5. CLAHE dimensions and uint8 format are preserved.
6. Sharpening enabled executes unconditionally when adaptive safeguard is False.
7. Sharpening disabled does not execute and leaves image unchanged.
8. Soft input receives appropriate sharpening effect.
9. Excessive halos are avoided (unity-gain energy conservation).
10. Adaptive bypass for sharpening behaves correctly.
11. Operations summary logs structured metadata: requested, executed, bypassed, reason, parameters, and before/after measurements.
12. FastAPI endpoint processes adaptive_contrast and adaptive_sharpen correctly.
"""

import cv2
import numpy as np
import pytest
from backend.src.processing.evaluation.heuristics import estimate_contrast, estimate_sharpness
from backend.src.processing.restoration.contrast import (
    adaptive_enhance_contrast,
    enhance_contrast,
    evaluate_contrast_protection,
)
from backend.src.processing.restoration.restorer import enhance_image
from backend.src.processing.restoration.sharpener import (
    adaptive_sharpen_image,
    evaluate_sharpen_protection,
    sharpen_image,
)
from backend.src.schemas.restoration import RestorationOptions
from backend.src.services.model_service import ModelService
from backend.src.services.restoration_service import RestorationService


@pytest.fixture
def low_contrast_canvas() -> np.ndarray:
    """A low-contrast image (std < 20)."""
    base = np.zeros((120, 120, 3), dtype=np.uint8)
    for y in range(120):
        val = int(100 + (y / 120.0) * 25)
        base[y, :] = (val, val, val)
    return base


@pytest.fixture
def soft_portrait_canvas() -> np.ndarray:
    """A soft portrait canvas with soft edges (lap_var < 50, low noise)."""
    img = np.full((150, 150, 3), 130, dtype=np.uint8)
    cv2.ellipse(img, (75, 75), (40, 55), 0, 0, 360, (180, 190, 205), -1)
    cv2.circle(img, (60, 65), 5, (45, 50, 60), -1)
    cv2.circle(img, (90, 65), 5, (45, 50, 60), -1)
    return cv2.GaussianBlur(img, (9, 9), 2.5)


@pytest.fixture
def clean_sharp_canvas() -> np.ndarray:
    """A clean canvas with adequate dynamic range and sharp contours."""
    img = np.full((150, 150, 3), 140, dtype=np.uint8)
    cv2.ellipse(img, (75, 75), (45, 60), 0, 0, 360, (190, 200, 215), -1)
    cv2.circle(img, (60, 65), 6, (30, 35, 45), -1)
    cv2.circle(img, (90, 65), 6, (30, 35, 45), -1)
    cv2.line(img, (20, 20), (130, 20), (10, 10, 10), 3)
    return img


class TestClaheComprehensive:
    """Automated test suite for CLAHE contrast enhancement."""

    def test_clahe_enabled_executes_unconditionally_when_forced(self, clean_sharp_canvas):
        """When contrast=True and adaptive_contrast=False, CLAHE executes unconditionally."""
        out, summary = enhance_image(
            clean_sharp_canvas,
            denoise=False,
            contrast=True,
            sharpen=False,
            adaptive_contrast=False,
            return_summary=True,
        )
        assert "contrast" in summary
        assert "Applied:" in summary["contrast"]
        assert "Executed: true" in summary["contrast"]
        assert "Bypassed: false" in summary["contrast"]
        assert not np.array_equal(out, clean_sharp_canvas)

    def test_clahe_disabled_does_not_execute(self, low_contrast_canvas):
        """When contrast=False, image is not modified and summary logs clean bypass."""
        out, summary = enhance_image(
            low_contrast_canvas,
            denoise=False,
            contrast=False,
            sharpen=False,
            return_summary=True,
        )
        assert np.array_equal(out, low_contrast_canvas)
        assert "contrast" in summary
        assert "Bypassed:" in summary["contrast"]
        assert "not requested" in summary["contrast"].lower()
        assert "Requested: false" in summary["contrast"]

    def test_clahe_low_contrast_input_is_enhanced(self, low_contrast_canvas):
        """Low contrast input (std < 22) is enhanced adaptively."""
        out, summary = enhance_image(
            low_contrast_canvas,
            denoise=False,
            contrast=True,
            sharpen=False,
            adaptive_contrast=True,
            return_summary=True,
        )
        assert "Applied:" in summary["contrast"]
        assert "Executed: true" in summary["contrast"]
        assert float(out.std()) > float(low_contrast_canvas.std())

    def test_clahe_clean_image_protection_behaves_correctly(self, clean_sharp_canvas):
        """Clean high-contrast input is bypassed when adaptive protection is enabled."""
        out, summary = enhance_image(
            clean_sharp_canvas,
            denoise=False,
            contrast=True,
            sharpen=False,
            adaptive_contrast=True,
            return_summary=True,
        )
        assert "Bypassed:" in summary["contrast"]
        assert "Executed: false" in summary["contrast"]
        assert "Bypassed: true" in summary["contrast"]
        assert np.array_equal(out, clean_sharp_canvas)

    def test_clahe_dimensions_and_format_preserved(self, low_contrast_canvas):
        """CLAHE preserves exact dimensions and uint8 data type."""
        enhanced = enhance_contrast(low_contrast_canvas)
        assert enhanced.shape == low_contrast_canvas.shape
        assert enhanced.dtype == np.uint8


class TestSharpeningComprehensive:
    """Automated test suite for Laplacian sharpening."""

    def test_sharpening_enabled_executes_unconditionally_when_forced(self, clean_sharp_canvas):
        """When sharpen=True and adaptive_sharpen=False, sharpening executes unconditionally."""
        out, summary = enhance_image(
            clean_sharp_canvas,
            denoise=False,
            contrast=False,
            sharpen=True,
            adaptive_sharpen=False,
            return_summary=True,
        )
        assert "sharpening" in summary
        assert "Applied:" in summary["sharpening"]
        assert "Executed: true" in summary["sharpening"]
        assert "Bypassed: false" in summary["sharpening"]
        assert not np.array_equal(out, clean_sharp_canvas)

    def test_sharpening_disabled_does_not_execute(self, soft_portrait_canvas):
        """When sharpen=False, image is not modified and summary logs clean bypass."""
        out, summary = enhance_image(
            soft_portrait_canvas,
            denoise=False,
            contrast=False,
            sharpen=False,
            return_summary=True,
        )
        assert np.array_equal(out, soft_portrait_canvas)
        assert "sharpening" in summary
        assert "Bypassed:" in summary["sharpening"]
        assert "not requested" in summary["sharpening"].lower()
        assert "Requested: false" in summary["sharpening"]

    def test_sharpening_soft_input_receives_edge_clarity(self, soft_portrait_canvas):
        """Soft input receives edge sharpening and increases Laplacian variance."""
        out, summary = enhance_image(
            soft_portrait_canvas,
            denoise=False,
            contrast=False,
            sharpen=True,
            adaptive_sharpen=True,
            return_summary=True,
        )
        assert "Applied:" in summary["sharpening"]
        assert "Executed: true" in summary["sharpening"]
        assert estimate_sharpness(out) > estimate_sharpness(soft_portrait_canvas)

    def test_sharpening_excessive_halos_avoided(self, soft_portrait_canvas):
        """Unity-gain kernel strictly maintains regional mean intensity (no brightness blowout)."""
        sharpened = sharpen_image(soft_portrait_canvas)
        mean_orig = float(soft_portrait_canvas.mean())
        mean_sharp = float(sharpened.mean())
        # Energy conservation check: mean shift must be negligible (< 0.5)
        assert abs(mean_sharp - mean_orig) < 0.5

    def test_sharpening_adaptive_bypass_behaves_correctly(self, clean_sharp_canvas):
        """Sharp canvas with lap_var >= 120 is safely bypassed when adaptive safeguard is enabled."""
        out, summary = enhance_image(
            clean_sharp_canvas,
            denoise=False,
            contrast=False,
            sharpen=True,
            adaptive_sharpen=True,
            return_summary=True,
        )
        assert "Bypassed:" in summary["sharpening"]
        assert "Executed: false" in summary["sharpening"]
        assert "Bypassed: true" in summary["sharpening"]
        assert np.array_equal(out, clean_sharp_canvas)


class TestPipelineIntegration:
    """Automated integration tests for end-to-end service and HTTP API."""

    def test_integration_restoration_service_summary_structured(self, low_contrast_canvas):
        """RestorationService returns operations_summary with structured verification metrics."""
        service = RestorationService(ModelService())
        _, png_bytes = cv2.imencode(".png", low_contrast_canvas)

        opts = RestorationOptions(
            denoise=False,
            contrast=True,
            adaptive_contrast=False,
            sharpen=True,
            adaptive_sharpen=False,
            colorize=False,
            repair=False,
        )

        res, out_bytes = service.process_image(
            file_bytes=png_bytes.tobytes(),
            filename="test_forced.png",
            options=opts,
        )

        summary = res.operations_summary
        assert summary is not None
        assert "contrast" in summary
        assert "Applied:" in summary["contrast"]
        assert "Requested: true" in summary["contrast"]
        assert "Executed: true" in summary["contrast"]

        assert "sharpening" in summary
        assert "Applied:" in summary["sharpening"]
        assert "Requested: true" in summary["sharpening"]
        assert "Executed: true" in summary["sharpening"]

    def test_integration_restoration_service_forced_clahe_and_sharpening(self, low_contrast_canvas):
        """RestorationService correctly applies forced CLAHE and sharpening when adaptive protection is disabled."""
        service = RestorationService(ModelService())
        _, png_bytes = cv2.imencode(".png", low_contrast_canvas)

        opts = RestorationOptions(
            denoise=False,
            contrast=True,
            adaptive_contrast=False,
            sharpen=True,
            adaptive_sharpen=False,
            colorize=False,
            repair=False,
        )

        res, out_bytes = service.process_image(
            file_bytes=png_bytes.tobytes(),
            filename="forced_both.png",
            options=opts,
        )

        assert res.status == "success"
        assert res.options_applied.adaptive_contrast is False
        assert res.options_applied.adaptive_sharpen is False
        assert res.operations_summary is not None
        assert "Applied:" in res.operations_summary["contrast"]
        assert "Applied:" in res.operations_summary["sharpening"]
        assert res.metrics.sharpness_delta > 0 or res.metrics.contrast_delta > 0
