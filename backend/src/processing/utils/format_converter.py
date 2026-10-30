"""Module: format_converter.py

Purpose:
Provides image format encoding and byte conversion utilities.

Responsibilities:
- Encode NumPy RGB uint8 arrays into standard base64-encoded PNG data URIs.
- Convert raw byte counts into human-readable strings (e.g. "1.5 KB", "4.8 MB").

Inputs:
- image_array: uint8 NumPy array of shape (H, W, 3).
- num_bytes: Integer byte count.

Outputs:
- String data URI or human-readable file size string.

Dependencies:
- base64
- io
- numpy
- PIL.Image

This module does not:
- Handle web endpoints directly.
- Perform geometric resizing or filtering.
"""

import base64
import io

import numpy as np
from PIL import Image


def image_to_base64_png(image_array: np.ndarray) -> str:
    """Encode an RGB uint8 NumPy array as a base64 PNG data URI string.

    Args:
        image_array:
            RGB uint8 NumPy array of shape (height, width, 3).

    Returns:
        String prefixed with 'data:image/png;base64,...'.
    """
    if not isinstance(image_array, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")

    pil_image = Image.fromarray(image_array)
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def format_file_size(num_bytes: int) -> str:
    """Convert an integer byte count into a human-readable file size string.

    Examples:
        500 -> '500 B'
        2048 -> '2.0 KB'
        5000000 -> '4.8 MB'

    Args:
        num_bytes:
            Integer number of bytes.

    Returns:
        Formatted human-readable string.
    """
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GB"

