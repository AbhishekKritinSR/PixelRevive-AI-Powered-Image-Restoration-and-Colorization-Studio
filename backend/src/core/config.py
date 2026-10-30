"""Module: config.py

Purpose:
Provides centralized, validated configuration for the FastAPI backend service.

Responsibilities:
- Define application name, API version, and description.
- Configure CORS origins for frontend client communication.
- Define upload size thresholds and allowed image MIME types.
- Import and re-export Phase 1 domain paths and processing limits from `src.config`
  to maintain a single source of truth without duplicating constants.

Dependencies:
- pathlib.Path
- src.config (PROJECT_ROOT, MODEL_DIR, PROTOTXT_PATH, MODEL_PATH, POINTS_PATH,
              MAX_IMAGE_DIMENSION, MAX_BATCH_FILES)
"""

from pathlib import Path
from typing import List, Set

from src.config import (
    MAX_BATCH_FILES,
    MAX_IMAGE_DIMENSION,
    MODEL_DIR,
    MODEL_PATH,
    POINTS_PATH,
    PROJECT_ROOT,
    PROTOTXT_PATH,
)


class Settings:
    """Centralized application settings for the FastAPI backend service."""

    # Project Information
    PROJECT_NAME: str = "AI Photo Restoration & Colorization Studio"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DESCRIPTION: str = (
        "High-performance REST API for digital photograph restoration and "
        "AI-based colorization using OpenCV and the Zhang et al. (ECCV 2016) model."
    )

    # CORS Configuration (allows local frontend development servers)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8501",  # Streamlit
    ]

    # File Upload Limits
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB per image
    ALLOWED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp"}
    ALLOWED_IMAGE_MIME_TYPES: Set[str] = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    # Image Processing Limits (from src.config)
    MAX_IMAGE_DIMENSION: int = MAX_IMAGE_DIMENSION  # 1600px cap
    MAX_BATCH_FILES: int = MAX_BATCH_FILES          # 10 images cap

    # Model Storage Paths (from src.config)
    PROJECT_ROOT: Path = PROJECT_ROOT
    MODEL_DIR: Path = MODEL_DIR
    PROTOTXT_PATH: Path = PROTOTXT_PATH
    MODEL_PATH: Path = MODEL_PATH
    POINTS_PATH: Path = POINTS_PATH


# Global settings singleton
settings = Settings()

