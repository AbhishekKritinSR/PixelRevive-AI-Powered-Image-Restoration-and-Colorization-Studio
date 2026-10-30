"""Image processing and data serialization utilities subpackage.

Provides:
- Aspect-preserving downscaling (geometry.py)
- Base64 encoding and size formatting (format_converter.py)
- In-memory ZIP packaging (zip_builder.py)
"""

from .format_converter import format_file_size, image_to_base64_png
from .geometry import resize_if_too_large
from .zip_builder import build_results_zip

__all__ = [
    "resize_if_too_large",
    "image_to_base64_png",
    "format_file_size",
    "build_results_zip",
]

