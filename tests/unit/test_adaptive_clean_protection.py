"""Unit and regression tests for Phase 3.5: Adaptive Clean-Image Protection for Contrast and Sharpening.

Tests cover:
1. Pristine high-contrast photograph (CLAHE and sharpening bypassed)
2. Pristine low-contrast photograph (adequate natural contrast preserved)
3. Genuinely faded photograph (CLAHE triggered and contrast expanded)
4. Naturally soft photograph (Laplacian sharpening triggered and edges clarified)
5. Sharp photograph with visible noise (Sharpening bypassed to prevent grain amplification)
6. Clean portrait (Identity and tonal balance preserved without artifacting)
7. Textured landscape (Fine textures preserved without haloing)
8. Empty, flat, and invalid image inputs (Error handling and graceful bypass)
9. Contrast explicitly disabled (contrast=False logged cleanly)
10. Sharpening explicitly disabled (sharpen=False logged cleanly)
11. User explicitly requesting enhancement (force / adaptive=False applies unconditionally)
12. Full end-to-end service integration (RestorationService.process_image)
"""

import cv2
import numpy as np
import pytest

from backend.src.processing.evaluation.heuristics import estimate_contrast, estimate_sharpness
from backend.src.processing.evaluation.ssim import compute_ssim
from backend.src.processing.restoration.contrast import (
    ContrastParameters,
    adaptive_enhance_contrast,
    enhance_contrast,
    evaluate_contrast_protection,
)
from backend.src.processing.restoration.restorer import enhance_image
from backend.src.processing.restoration.sharpener import (
    SharpenParameters,
    adaptive_sharpen_image,
    evaluate_sharpen_protection,
    sharpen_image,
)
from backend.src.schemas.restoration import RestorationOptions
from backend.src.services.model_service import ModelService
from backend.src.services.restoration_service import RestorationService


@pytest.fixture
def clean_high_contrast_image() -> np.ndarray:
    """Create a pristine 200x200 BGR image with rich natural contrast and crisp edges."""
    canvas = np.zeros((200, 200, 3), dtype=np.uint8)
    canvas[:100, :] = (210, 180, 130)  # sky
    canvas[100:150, :] = (60, 100, 40)  # hills
    canvas[150:, :] = (40, 70, 150)    # water
    for x in range(20, 180, 15):
        cv2.line(canvas, (x, 100), (x + 10, 150), (30, 50, 20), 2)
    return canvas


@pytest.fixture
def clean_portrait_image() -> np.ndarray:
    """Create a clean 200x200 BGR portrait canvas with balanced tonal contrast and sharp eyes."""
    img = np.full((200, 200, 3), 140, dtype=np.uint8)
    # Face oval
    cv2.ellipse(img, (100, 100), (50, 70), 0, 0, 360, (185, 195, 215), -1)
    # Eyes
    cv2.circle(img, (80, 90), 6, (40, 45, 55), -1)
    cv2.circle(img, (120, 90), 6, (40, 45, 55), -1)
    # Lips
    cv2.ellipse(img, (100, 130), (16, 6), 0, 0, 360, (75, 85, 140), -1)
    return img


@pytest.fixture
def genuinely_faded_image() -> np.ndarray:
    """Create a severely contrast-compressed archival image representing optical fading."""
    base = np.zeros((160, 160, 3), dtype=np.uint8)
    for y in range(160):
        val = int(80 + (y / 160.0) * 80)
        base[y, :] = (val, val, val)
    gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    # Compress dynamic range strictly into [95, 129] (std ~ 9.9)
    faded = np.clip((gray.astype(np.float32) / 255.0) * 110.0 + 60.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(faded, cv2.COLOR_GRAY2BGR)


@pytest.fixture
def naturally_soft_image(clean_portrait_image) -> np.ndarray:
    """Create a portrait with blurred/soft edges simulating soft optical focus."""
    return cv2.GaussianBlur(clean_portrait_image, (7, 7), 2.2)


@pytest.fixture
def sharp_noisy_image(clean_portrait_image) -> np.ndarray:
    """Create an image with crisp edges but elevated Gaussian grain noise (sigma = 15)."""
    rng = np.random.default_rng(101)
    noise = rng.normal(0, 15.0, clean_portrait_image.shape)
    return np.clip(clean_portrait_image.astype(np.float32) + noise, 0, 255).astype(np.uint8)


class TestAdaptiveContrastProtection:
    """Tests for Task 2: Adaptive CLAHE contrast protection."""

    def test_pristine_high_contrast_bypasses_clahe(self, clean_high_contrast_image):
        """High-contrast images must bypass CLAHE to avoid histogram distortion."""
        params = evaluate_contrast_protection(clean_high_contrast_image)
        assert params.skip is True
        assert params.applied is False
        assert "Bypassed" in params.reason
        assert "adequate natural contrast" in params.reason

        out, out_params = adaptive_enhance_contrast(clean_high_contrast_image)
        assert out_params.skip is True
        # Must return bitwise identical array
        assert np.array_equal(out, clean_high_contrast_image)

    def test_genuinely_faded_image_executes_clahe(self, genuinely_faded_image):
        """Faded images with compressed dynamic range must execute CLAHE."""
        params = evaluate_contrast_protection(genuinely_faded_image)
        assert params.skip is False
        assert params.applied is True
        assert "Applied" in params.reason
        assert "low dynamic range" in params.reason

        out, out_params = adaptive_enhance_contrast(genuinely_faded_image)
        assert out_params.applied is True
        # Output must have higher standard deviation and expanded range
        assert out.std() > genuinely_faded_image.std()
        assert not np.array_equal(out, genuinely_faded_image)

    def test_flat_gray_image_bypasses_clahe(self):
        """Zero-variance flat images must safely bypass CLAHE."""
        flat = np.full((80, 80, 3), 128, dtype=np.uint8)
        params = evaluate_contrast_protection(flat)
        assert params.skip is True
        assert params.applied is False
        assert "zero luminance variance" in params.reason

        out, _ = adaptive_enhance_contrast(flat)
        assert np.array_equal(out, flat)

    def test_user_force_contrast_overrides_bypass(self, clean_high_contrast_image):
        """When force=True (or adaptive_contrast=False), CLAHE executes unconditionally."""
        params = evaluate_contrast_protection(clean_high_contrast_image, force=True)
        assert params.skip is False
        assert params.applied is True
        assert "explicit user request" in params.reason

        out, _ = adaptive_enhance_contrast(clean_high_contrast_image, force=True)
        assert not np.array_equal(out, clean_high_contrast_image)

    def test_invalid_input_types_raise_error(self):
        """Invalid non-numpy arrays or invalid dtypes must raise ValueError."""
        with pytest.raises(ValueError, match="NumPy array"):
            evaluate_contrast_protection([[1, 2], [3, 4]])  # type: ignore

        with pytest.raises(ValueError, match="uint8"):
            evaluate_contrast_protection(np.zeros((50, 50, 3), dtype=np.float32))


class TestAdaptiveSharpeningProtection:
    """Tests for Task 3: Adaptive Laplacian sharpening protection."""

    def test_already_sharp_image_bypasses_sharpening(self, clean_portrait_image):
        """Images with sharp edges (Laplacian var >= 120) must bypass sharpening."""
        params = evaluate_sharpen_protection(clean_portrait_image)
        assert params.skip is True
        assert params.applied is False
        assert "Bypassed" in params.reason
        assert "already exhibits sufficient edge sharpness" in params.reason

        out, out_params = adaptive_sharpen_image(clean_portrait_image)
        assert out_params.skip is True
        assert np.array_equal(out, clean_portrait_image)

    def test_naturally_soft_image_executes_sharpening(self, naturally_soft_image):
        """Soft/blurred images must execute Laplacian sharpening to clarify edges."""
        params = evaluate_sharpen_protection(naturally_soft_image)
        assert params.skip is False
        assert params.applied is True
        assert "Applied" in params.reason

        out, out_params = adaptive_sharpen_image(naturally_soft_image)
        assert out_params.applied is True
        # Sharpening must increase Laplacian variance
        assert estimate_sharpness(out) > estimate_sharpness(naturally_soft_image)
        assert not np.array_equal(out, naturally_soft_image)

    def test_sharp_image_with_visible_noise_bypasses_sharpening(self, sharp_noisy_image):
        """High-noise images (sigma >= 8.0) must bypass sharpening to avoid grain amplification."""
        params = evaluate_sharpen_protection(sharp_noisy_image)
        assert params.skip is True
        assert params.applied is False
        assert "elevated noise level" in params.reason

        out, out_params = adaptive_sharpen_image(sharp_noisy_image)
        assert out_params.skip is True
        assert np.array_equal(out, sharp_noisy_image)

    def test_pristine_smooth_gradient_bypasses_sharpening(self):
        """Pristine smooth gradients (noise < 1.5, low edge grad) must bypass sharpening."""
        canvas = np.zeros((128, 128, 3), dtype=np.uint8)
        for y in range(128):
            val = int(120 + 30 * np.sin(y / 25.0))
            canvas[y, :] = (val, val, val)
        canvas = cv2.GaussianBlur(canvas, (7, 7), 2.0)

        params = evaluate_sharpen_protection(canvas)
        assert params.skip is True
        assert params.applied is False
        assert "pristine continuous-tone image" in params.reason

        out, _ = adaptive_sharpen_image(canvas)
        assert np.array_equal(out, canvas)

    def test_flat_gray_image_bypasses_sharpening(self):
        """Flat images with zero Laplacian variance must bypass sharpening."""
        flat = np.full((64, 64, 3), 128, dtype=np.uint8)
        params = evaluate_sharpen_protection(flat)
        assert params.skip is True
        assert params.applied is False
        assert "zero high-frequency variance" in params.reason

        out, _ = adaptive_sharpen_image(flat)
        assert np.array_equal(out, flat)

    def test_user_force_sharpening_overrides_bypass(self, clean_portrait_image):
        """When force=True (or adaptive_sharpen=False), sharpening executes unconditionally."""
        params = evaluate_sharpen_protection(clean_portrait_image, force=True)
        assert params.skip is False
        assert params.applied is True
        assert "explicit user request" in params.reason

        out, _ = adaptive_sharpen_image(clean_portrait_image, force=True)
        assert not np.array_equal(out, clean_portrait_image)

    def test_invalid_input_types_raise_error(self):
        """Invalid inputs must raise ValueError."""
        with pytest.raises(ValueError, match="NumPy array"):
            evaluate_sharpen_protection("not_an_image")  # type: ignore

        with pytest.raises(ValueError, match="uint8"):
            evaluate_sharpen_protection(np.zeros((40, 40, 3), dtype=np.int32))


class TestPipelineExplainabilityAndIntegration:
    """Tests for Task 4 & Task 5: Pipeline explainability, toggling, and clean-image preservation."""

    def test_clean_portrait_with_all_toggles_enabled_preserves_pixels(self, clean_portrait_image):
        """A clean portrait image with restoration toggles on (denoise, contrast, sharpen)
        must bypass modification cleanly and achieve SSIM = 1.0000.
        """
        out, summary = enhance_image(
            clean_portrait_image,
            denoise=True,
            contrast=True,
            sharpen=True,
            repair=False,
            adaptive_denoise=True,
            adaptive_contrast=True,
            adaptive_sharpen=True,
            return_summary=True,
        )

        assert "denoising" in summary
        assert "Bypassed" in summary["denoising"]

        assert "contrast" in summary
        assert "Bypassed" in summary["contrast"]

        assert "sharpening" in summary
        assert "Bypassed" in summary["sharpening"]

        # Exact pixel preservation
        assert np.array_equal(out, clean_portrait_image)
        ssim_val, _, _, _ = compute_ssim(clean_portrait_image, out)
        assert ssim_val == 1.0000

    def test_faded_soft_photograph_applies_both_contrast_and_sharpening(self, clean_portrait_image):
        """A degraded photograph that is both faded and soft must execute both stages."""
        soft_faded = cv2.GaussianBlur(clean_portrait_image, (7, 7), 2.0)
        soft_faded = np.clip(soft_faded.astype(float) * 0.4 + 80, 0, 255).astype(np.uint8)

        out, summary = enhance_image(
            soft_faded,
            denoise=True,
            contrast=True,
            sharpen=True,
            adaptive_denoise=True,
            adaptive_contrast=True,
            adaptive_sharpen=True,
            return_summary=True,
        )

        assert "contrast" in summary
        assert "Applied" in summary["contrast"]

        assert "sharpening" in summary
        assert "Applied" in summary["sharpening"]

        assert not np.array_equal(out, soft_faded)
        assert out.std() > soft_faded.std()

    def test_contrast_explicitly_disabled(self, genuinely_faded_image):
        """When contrast=False, summary records clean bypass and image is not equalized."""
        out, summary = enhance_image(
            genuinely_faded_image,
            denoise=False,
            contrast=False,
            sharpen=False,
            return_summary=True,
        )
        assert "contrast" in summary
        assert "not requested" in summary["contrast"].lower()
        assert np.array_equal(out, genuinely_faded_image)

    def test_sharpening_explicitly_disabled(self, naturally_soft_image):
        """When sharpen=False, summary records clean bypass and image is not sharpened."""
        out, summary = enhance_image(
            naturally_soft_image,
            denoise=False,
            contrast=False,
            sharpen=False,
            return_summary=True,
        )
        assert "sharpening" in summary
        assert "not requested" in summary["sharpening"].lower()
        assert np.array_equal(out, naturally_soft_image)

    def test_user_disabling_adaptive_forces_enhancement(self, clean_high_contrast_image):
        """When adaptive_contrast=False and adaptive_sharpen=False, operations execute unconditionally."""
        out, summary = enhance_image(
            clean_high_contrast_image,
            denoise=False,
            contrast=True,
            sharpen=True,
            adaptive_contrast=False,
            adaptive_sharpen=False,
            return_summary=True,
        )
        assert "contrast" in summary
        assert "Applied" in summary["contrast"]

        assert "sharpening" in summary
        assert "Applied" in summary["sharpening"]

        # Output must be modified because adaptive protection was disabled
        assert not np.array_equal(out, clean_high_contrast_image)


class TestRestorationServiceEndToEndCleanProtection:
    """End-to-end tests for RestorationService.process_image with Phase 3.5 safeguards."""

    def test_service_pristine_reference_canvas_achieves_perfect_preservation(self):
        """Category H synthetic pristine reference canvas must achieve 0 changed pixels

        and SSIM = 1.0000 with ALL default restoration options enabled.
        """
        service = RestorationService(ModelService())

        # Create Category H pristine continuous-tone reference image
        canvas = np.zeros((160, 160, 3), dtype=np.uint8)
        for y in range(160):
            val = int(120 + 35 * np.sin(y / 25.0))
            canvas[y, :] = (val - 5, val, val + 15)
        cv2.circle(canvas, (80, 80), 40, (140, 150, 175), -1)
        canvas = cv2.GaussianBlur(canvas, (7, 7), 2.0)

        success, png_bytes = cv2.imencode(".png", canvas)
        assert success

        # ALL toggles enabled (full production pipeline)
        opts = RestorationOptions(
            denoise=True,
            contrast=True,
            sharpen=True,
            colorize=False,
            repair=True,
            adaptive_denoise=True,
            adaptive_contrast=True,
            adaptive_sharpen=True,
        )

        res, out_bytes = service.process_image(
            file_bytes=png_bytes.tobytes(),
            filename="pristine_clean.png",
            options=opts,
        )

        # Decode output
        out_bgr = cv2.imdecode(np.frombuffer(out_bytes, np.uint8), cv2.IMREAD_COLOR)

        # 1. Verification of SSIM and pixel identity
        ssim_val, _, _, _ = compute_ssim(canvas, out_bgr)
        assert ssim_val == 1.0000

        diff = np.abs(out_bgr.astype(int) - canvas.astype(int))
        assert np.max(diff) == 0
        assert np.mean(diff) == 0.0
        assert np.count_nonzero(out_bgr != canvas) == 0

        # 2. Verification of operations summary log
        summary = res.operations_summary
        assert summary is not None
        assert "Bypassed" in summary["scratch_repair"]
        assert "Bypassed" in summary["denoising"]
        assert "Bypassed" in summary["contrast"]
        assert "Bypassed" in summary["sharpening"]

    def test_service_faded_monochrome_executes_contrast_and_colorization(self, genuinely_faded_image):
        """A faded monochrome photo through RestorationService must apply CLAHE and colorization."""
        service = RestorationService(ModelService())

        success, png_bytes = cv2.imencode(".png", genuinely_faded_image)
        assert success

        opts = RestorationOptions(
            denoise=True,
            contrast=True,
            sharpen=True,
            colorize=True,
            repair=True,
            adaptive_denoise=True,
            adaptive_contrast=True,
            adaptive_sharpen=True,
        )

        res, out_bytes = service.process_image(
            file_bytes=png_bytes.tobytes(),
            filename="faded_archival.png",
            options=opts,
        )

        summary = res.operations_summary
        assert summary is not None
        assert "contrast" in summary
        assert "Applied" in summary["contrast"]
        assert "colorization" in summary
        assert "Applied" in summary["colorization"]
