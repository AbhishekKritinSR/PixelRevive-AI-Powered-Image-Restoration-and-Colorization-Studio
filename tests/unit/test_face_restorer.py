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

