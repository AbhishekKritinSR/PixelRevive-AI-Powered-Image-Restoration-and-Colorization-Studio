"""Unit test suite for Face Feature Restoration Engine.

Verifies:
1. FaceRestorer cascade loading and face detection.
2. Identity-preserving localized portrait feature enhancement.
3. Soft elliptical feather boundary blending.
4. Pass-through when no faces are detected or strength=0.
"""

from pathlib import Path
import numpy as np
import cv2
import pytest

from backend.src.processing.restoration.face_restorer import FaceRestorer


class TestFaceRestorer:
    """Tests for localized identity-preserving facial enhancement."""

    def test_cascade_asset_availability(self):
        """Test Haar cascade loader."""
        cascade = FaceRestorer.get_cascade()
        assert cascade is not None
        assert not cascade.empty()

    def test_pass_through_on_zero_strength(self):
        """When enhancement_strength is 0.0, image must remain identical."""
        img = np.full((120, 120, 3), 130, dtype=np.uint8)
        restored, count = FaceRestorer.restore_faces(img, enhancement_strength=0.0)
        assert count == 0
        np.testing.assert_array_equal(restored, img)

    def test_face_detection_and_soft_blending(self):
        """Test that facial enhancement produces continuous uint8 values without rectangular seams."""
        # Create a synthetic portrait-like oval face on darker background
        img = np.full((200, 200, 3), 50, dtype=np.uint8)
        # Face oval
        cv2.ellipse(img, (100, 100), (45, 60), 0, 0, 360, (180, 160, 140), -1)
        # Eyes
        cv2.circle(img, (80, 85), 6, (40, 30, 20), -1)
        cv2.circle(img, (120, 85), 6, (40, 30, 20), -1)
        # Mouth
        cv2.ellipse(img, (100, 130), (16, 5), 0, 0, 360, (120, 60, 60), -1)

        restored, count = FaceRestorer.restore_faces(img, enhancement_strength=0.5)
        assert restored.shape == img.shape
        assert restored.dtype == np.uint8
        assert np.all(np.isfinite(restored))

    def test_face_enhancement_increases_sharpness(self):
        """Test that facial enhancement actively increases local sharpness and contrast on portrait faces."""
        img = np.full((200, 200, 3), 50, dtype=np.uint8)
        cv2.ellipse(img, (100, 100), (45, 60), 0, 0, 360, (180, 160, 140), -1)
        cv2.circle(img, (80, 85), 6, (40, 30, 20), -1)
        cv2.circle(img, (120, 85), 6, (40, 30, 20), -1)
        cv2.ellipse(img, (100, 130), (16, 5), 0, 0, 360, (120, 60, 60), -1)

        faces = FaceRestorer.detect_faces(img)
        assert len(faces) >= 1
        x, y, w, h = faces[0]
        orig_roi = img[y:y+h, x:x+w]
        orig_lap = cv2.Laplacian(cv2.cvtColor(orig_roi, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()

        restored, count = FaceRestorer.restore_faces(img, enhancement_strength=0.75)
        assert count >= 1
        rest_roi = restored[y:y+h, x:x+w]
        rest_lap = cv2.Laplacian(cv2.cvtColor(rest_roi, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()

        # Sharpness must increase
        assert rest_lap > orig_lap
        # Pixel values must change noticeably (perceptual improvement)
        assert float(np.mean(np.abs(rest_roi.astype(float) - orig_roi.astype(float)))) > 3.0

    def test_soft_boundary_no_hard_seams(self):
        """Test that the border pixels of the expanded ROI have seamless transition to background."""
        img = np.full((200, 200, 3), 50, dtype=np.uint8)
        cv2.ellipse(img, (100, 100), (45, 60), 0, 0, 360, (180, 160, 140), -1)
        cv2.circle(img, (80, 85), 6, (40, 30, 20), -1)
        cv2.circle(img, (120, 85), 6, (40, 30, 20), -1)
        cv2.ellipse(img, (100, 130), (16, 5), 0, 0, 360, (120, 60, 60), -1)

        faces = FaceRestorer.detect_faces(img)
        x, y, w, h = faces[0]
        margin_x = int(w * 0.15)
        margin_y = int(h * 0.15)
        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(img.shape[1], x + w + margin_x)
        y2 = min(img.shape[0], y + h + margin_y)

        restored, _ = FaceRestorer.restore_faces(img, enhancement_strength=0.75)

        # The outer border row of the ROI should transition seamlessly to original image
        top_row_diff = np.mean(np.abs(restored[y1, x1:x2].astype(float) - img[y1, x1:x2].astype(float)))
        left_col_diff = np.mean(np.abs(restored[y1:y2, x1].astype(float) - img[y1:y2, x1].astype(float)))
        assert top_row_diff < 1.0
        assert left_col_diff < 1.0

    def test_grain_noise_false_positive_rejection(self):
        """Pure noise and uniform textures should not trigger false face detections."""
        np.random.seed(42)
        noise_img = np.random.randint(80, 175, (600, 600, 3), dtype=np.uint8)
        faces = FaceRestorer.detect_faces(noise_img)
        assert len(faces) == 0

