"""Module: zip_builder.py

Purpose:
Packages multiple named byte streams into an in-memory ZIP archive.

Responsibilities:
- Bundle a sequence of (filename, file_bytes) pairs into a single in-memory ZIP.
- Use standard ZIP_DEFLATED compression.
- Return raw ZIP bytes ready for file streaming or download response.

Inputs:
- named_file_bytes: Iterable sequence of tuples (filename_str, bytes_data).

Outputs:
- bytes: Complete in-memory ZIP file content.

Dependencies:
- io
- zipfile

This module does not:
- Write files to permanent disk storage.
- Manage temporary files or directories.
"""

import io
from typing import Iterable, Tuple
import zipfile


def build_results_zip(named_file_bytes: Iterable[Tuple[str, bytes]]) -> bytes:
    """Bundle (filename, bytes) pairs into one in-memory ZIP archive.

    Args:
        named_file_bytes:
            Iterable of (filename, data_bytes) tuples to add into the ZIP.

    Returns:
        Raw bytes of the assembled ZIP file.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in named_file_bytes:
            zf.writestr(filename, data)
    return buf.getvalue()

