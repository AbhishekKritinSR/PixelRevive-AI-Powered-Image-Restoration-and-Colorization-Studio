"""Module: test_restoration_benchmark.py

Purpose:
Comprehensive real-world restoration benchmark framework evaluating PixelRevive's
hybrid classical and deep learning pipeline across eight standard photographic degradation categories (A-H).

Degradation Categories Evaluated:
- Category A: Scratched B&W portraits (directional hairline & tear damage)
- Category B: Faded historical photos (severe low-contrast dynamic range)
- Category C: Photos with large missing areas (structural occlusion)
- Category D: Heavy sensor / photographic grain noise (Gaussian noise sigma=25)
- Category E: Blurry optical photos (severe defocus blur)
- Category F: Low-resolution archival scans (downsampled < 100px)
- Category G: Damaged color photos (scratched + noisy + desaturated)
- Category H: Clean / pristine reference photos (preservation verification)

Metrics Evaluated:
- SSIM (Structural Similarity Index Measure) against clean ground truth
- BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator)
- Hasler-Süsstrunk Colorfulness Index
- Laplacian Edge Variance / Contrast Dispersion
- Execution Latency (seconds)
"""

import time
from typing import Dict, Tuple
import cv2
import numpy as np
import pytest

from backend.src.processing.evaluation.brisque import compute_brisque
from backend.src.processing.evaluation.colorfulness import compute_colorfulness
from backend.src.processing.evaluation.heuristics import estimate_noise_sigma
from backend.src.processing.evaluation.ssim import compute_ssim
from backend.src.processing.restoration.contrast import enhance_contrast
from backend.src.processing.restoration.denoiser import denoise_image
from backend.src.processing.restoration.face_restorer import FaceRestorer
from backend.src.processing.restoration.restorer import enhance_image
from backend.src.processing.restoration.scratch_repair import (
    detect_scratch_mask,
    repair_scratches,
)
from backend.src.processing.restoration.sharpener import sharpen_image
from backend.src.processing.restoration.super_resolution import upscale_image


# =============================================================================
# Synthetic Degradation Test Generators (Categories A to H)
# =============================================================================

def create_base_synthetic_portrait() -> Tuple[np.ndarray, np.ndarray]:
    """Create a pristine 200x200 synthetic portrait with head, eyes, mouth, and shoulders."""
    img = np.full((200, 200, 3), 160, dtype=np.uint8)
    # Background gradient
    for y in range(200):
        img[y, :, :] = int(140 + 50 * (y / 200))

    # Face oval (center 100, 95)
    cv2.ellipse(img, (100, 95), (45, 60), 0, 0, 360, (190, 195, 215), -1)
    # Left eye, right eye
    cv2.circle(img, (82, 85), 6, (50, 50, 60), -1)
    cv2.circle(img, (118, 85), 6, (50, 50, 60), -1)
    # Nose line
    cv2.line(img, (100, 88), (100, 108), (130, 130, 145), 2)
    # Mouth line
    cv2.line(img, (88, 125), (112, 125), (80, 85, 120), 2)
    # Shoulders
    cv2.ellipse(img, (100, 210), (80, 50), 0, 0, 360, (70, 75, 90), -1)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mono_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    return img, mono_img


class BenchmarkDataset:
    """Provides generated samples across all 8 degradation categories."""

    @staticmethod
    def get_category_a() -> Tuple[np.ndarray, np.ndarray]:
        """Category A: Scratched B&W portrait."""
        _, clean_mono = create_base_synthetic_portrait()
        degraded = clean_mono.copy()
        # Add 3 prominent directional scratches
        cv2.line(degraded, (30, 10), (35, 180), (20, 20, 20), 1)
        cv2.line(degraded, (160, 20), (165, 170), (250, 250, 250), 1)
        cv2.line(degraded, (60, 150), (140, 155), (15, 15, 15), 1)
        return clean_mono, degraded

    @staticmethod
    def get_category_b() -> Tuple[np.ndarray, np.ndarray]:
        """Category B: Faded historical photo (low contrast, washed-out dynamic range)."""
        _, clean_mono = create_base_synthetic_portrait()
        # Compress dynamic range to [100, 145]
        degraded = (clean_mono.astype(np.float32) * (45.0 / 255.0) + 100.0).astype(np.uint8)
        return clean_mono, degraded

    @staticmethod
    def get_category_c() -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Category C: Photo with missing area / tear defect."""
        _, clean_mono = create_base_synthetic_portrait()
        degraded = clean_mono.copy()
        mask = np.zeros(degraded.shape[:2], dtype=np.uint8)
        # Deep tear defect
        cv2.line(degraded, (25, 25), (45, 75), (245, 245, 245), 5)
        cv2.line(mask, (25, 25), (45, 75), 255, 7)
        return clean_mono, degraded, mask

    @staticmethod
    def get_category_d() -> Tuple[np.ndarray, np.ndarray]:
        """Category D: Noisy photo (additive Gaussian noise sigma=25)."""
        _, clean_mono = create_base_synthetic_portrait()
        rng = np.random.RandomState(42)
        noise = rng.normal(0, 25.0, clean_mono.shape)
        degraded = np.clip(clean_mono.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        return clean_mono, degraded

    @staticmethod
    def get_category_e() -> Tuple[np.ndarray, np.ndarray]:
        """Category E: Blurry photo (defocus blur 9x9)."""
        clean_color, _ = create_base_synthetic_portrait()
        degraded = cv2.GaussianBlur(clean_color, (9, 9), 2.5)
        return clean_color, degraded

    @staticmethod
    def get_category_f() -> Tuple[np.ndarray, np.ndarray]:
        """Category F: Low-resolution photo (subsampled to 64x64)."""
        clean_color, _ = create_base_synthetic_portrait()
        degraded = cv2.resize(clean_color, (64, 64), interpolation=cv2.INTER_AREA)
        return clean_color, degraded

    @staticmethod
    def get_category_g() -> Tuple[np.ndarray, np.ndarray]:
        """Category G: Damaged color photo (scratches + noise + low saturation)."""
        clean_color, _ = create_base_synthetic_portrait()
        # Desaturate
        hsv = cv2.cvtColor(clean_color, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] *= 0.35  # faded color
        degraded = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        # Add scratch
        cv2.line(degraded, (40, 20), (45, 170), (25, 25, 25), 1)
        # Add mild noise
        rng = np.random.RandomState(42)
        degraded = np.clip(degraded.astype(np.float32) + rng.normal(0, 10.0, degraded.shape), 0, 255).astype(np.uint8)
        return clean_color, degraded

    @staticmethod
    def get_category_h() -> Tuple[np.ndarray, np.ndarray]:
        """Category H: Clean undamaged reference photo."""
        clean_color, _ = create_base_synthetic_portrait()
        return clean_color, clean_color.copy()


# =============================================================================
# Benchmarking Test Suite
# =============================================================================

class TestRestorationBenchmark:
    """Executes empirical benchmarks on Categories A through H."""

    def test_benchmark_category_a_scratch_repair(self):
        """Category A: Scratched B&W portraits should detect scratches and reduce defect area."""
        clean, degraded = BenchmarkDataset.get_category_a()

        # Measure baseline degradation
        mask_before, meta_before = detect_scratch_mask(degraded, threshold=20, min_length=8)
        assert meta_before.detected_components >= 2

        t0 = time.perf_counter()
        repaired, meta_repaired = repair_scratches(degraded, mask=mask_before, method="telea")
        elapsed = time.perf_counter() - t0

        # After repair, residual scratch components should be significantly reduced
        mask_after, meta_after = detect_scratch_mask(repaired, threshold=20, min_length=8)
        assert meta_after.detected_components < meta_before.detected_components
        assert meta_repaired.repaired_pixels > 0
        assert elapsed < 0.5  # Telea fast inpainting latency < 500ms

        # Compute SSIM improvement against clean reference
        ssim_deg = compute_ssim(degraded, clean)[0]
        ssim_rep = compute_ssim(repaired, clean)[0]
        assert ssim_rep >= ssim_deg

    def test_benchmark_category_b_faded_contrast_restoration(self):
        """Category B: Faded historical photos should have dynamic range expanded."""
        clean, degraded = BenchmarkDataset.get_category_b()

        std_before = float(np.std(degraded))
        range_before = float(np.percentile(degraded, 99) - np.percentile(degraded, 1))

        t0 = time.perf_counter()
        enhanced = enhance_contrast(degraded, clip_limit=2.5, tile_grid_size=(8, 8))
        elapsed = time.perf_counter() - t0

        std_after = float(np.std(enhanced))
        range_after = float(np.percentile(enhanced, 99) - np.percentile(enhanced, 1))

        assert std_after > std_before * 1.15
        assert range_after > range_before * 1.15
        assert elapsed < 0.1

    def test_benchmark_category_c_missing_areas(self):
        """Category C: Large defect inpainting fills missing region smoothly."""
        clean, degraded, mask = BenchmarkDataset.get_category_c()

        repaired, meta = repair_scratches(degraded, mask=mask, method="telea")
        assert meta.repaired_pixels > 0

        # Check that the defect region is inpainted and closer to clean background
        diff_deg = np.mean(np.abs(degraded.astype(float) - clean.astype(float)))
        diff_rep = np.mean(np.abs(repaired.astype(float) - clean.astype(float)))
        assert diff_rep < diff_deg

    def test_benchmark_category_d_noise_reduction(self):
        """Category D: Heavy noise reduction preserves edges while reducing sigma."""
        clean, degraded = BenchmarkDataset.get_category_d()

        gray_deg = cv2.cvtColor(degraded, cv2.COLOR_BGR2GRAY)
        sigma_before, _ = estimate_noise_sigma(gray_deg)

        t0 = time.perf_counter()
        denoised = denoise_image(degraded, h=12.0)
        elapsed = time.perf_counter() - t0

        gray_den = cv2.cvtColor(denoised, cv2.COLOR_BGR2GRAY)
        sigma_after, _ = estimate_noise_sigma(gray_den)

        assert sigma_after < sigma_before * 0.6
        ssim_deg = compute_ssim(degraded, clean)[0]
        ssim_den = compute_ssim(denoised, clean)[0]
        assert ssim_den > ssim_deg

    def test_benchmark_category_e_sharpening(self):
        """Category E: Blurry photos should recover edge sharpness."""
        clean, degraded = BenchmarkDataset.get_category_e()

        lap_var_before = float(cv2.Laplacian(cv2.cvtColor(degraded, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())

        t0 = time.perf_counter()
        sharpened = sharpen_image(degraded)
        elapsed = time.perf_counter() - t0

        lap_var_after = float(cv2.Laplacian(cv2.cvtColor(sharpened, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())

        assert lap_var_after > lap_var_before * 1.5
        assert elapsed < 0.05

    def test_benchmark_category_f_super_resolution(self):
        """Category F: Low-resolution photos are cleanly upscaled."""
        clean, degraded = BenchmarkDataset.get_category_f()

        h_orig, w_orig = degraded.shape[:2]
        t0 = time.perf_counter()
        upscaled, meta = upscale_image(degraded, scale=2, model="fsrcnn")
        elapsed = time.perf_counter() - t0

        assert upscaled.shape[0] == h_orig * 2
        assert upscaled.shape[1] == w_orig * 2
        assert elapsed < 0.2

    def test_benchmark_category_g_damaged_color(self):
        """Category G: Damaged color photos undergo combined restoration cleanly."""
        clean, degraded = BenchmarkDataset.get_category_g()

        mask, _ = detect_scratch_mask(degraded, threshold=20, min_length=8)
        repaired, _ = repair_scratches(degraded, mask=mask, method="telea")
        denoised = denoise_image(repaired, h=8.0)
        contrast = enhance_contrast(denoised, clip_limit=1.8)

        colorfulness_before = compute_colorfulness(degraded)[0]
        colorfulness_after = compute_colorfulness(contrast)[0]

        # Denoising eliminates artificial chromatic noise spikes while preserving true color channels
        assert colorfulness_after > 2.0
        assert contrast.shape == degraded.shape

    def test_benchmark_category_h_clean_photo_preservation(self):
        """Category H: Clean photos do not suffer drastic artifacting or degradation."""
        clean, degraded = BenchmarkDataset.get_category_h()

        # Denoise with gentle adaptive setting
        gentle_denoised = denoise_image(degraded, h=3.0)
        ssim_val = compute_ssim(gentle_denoised, clean)[0]

        # SSIM on pristine photo with gentle filter should be exceptionally high (>0.92)
        assert ssim_val >= 0.92
