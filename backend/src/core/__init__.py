"""Core foundational package containing configuration, exceptions, and logging."""

from .config import settings
from .exceptions import (
    BatchSizeExceededError,
    CorruptedImageError,
    FileTooLargeError,
    ImageValidationError,
    ModelUnavailableError,
    UnsupportedFormatError,
)
from .logging_config import setup_logging

__all__ = [
    "settings",
    "setup_logging",
    "ImageValidationError",
    "CorruptedImageError",
    "UnsupportedFormatError",
    "FileTooLargeError",
    "BatchSizeExceededError",
    "ModelUnavailableError",
]

