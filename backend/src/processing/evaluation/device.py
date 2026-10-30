"""Module: device.py

Purpose:
Inspects available hardware acceleration and reports the active execution device.

Responsibilities:
- Query OpenCV's CUDA subsystem for available GPU devices.
- Return "CUDA" if a compatible GPU device is detected and supported.
- Return "CPU" gracefully if CUDA is absent, disabled, or raises an error.
- Never raise an exception or crash the application.

Dependencies:
- cv2 (OpenCV)

This module does not:
- Initialize PyTorch, TensorFlow, or CUDA drivers.
- Switch devices dynamically.
"""

import cv2


def get_processing_device() -> str:
    """Return 'CUDA' if OpenCV was built with CUDA support and a device is present; 'CPU' otherwise.

    Standard `opencv-python-headless` distributions are CPU-only builds. This function
    honestly reports 'CPU' in that environment, and will seamlessly report 'CUDA' if
    deployed in an environment with a CUDA-enabled OpenCV build.

    Returns:
        String: Either 'CUDA' or 'CPU'. Never raises an exception.
    """
    try:
        if hasattr(cv2, "cuda") and cv2.cuda.getCudaEnabledDeviceCount() > 0:
            return "CUDA"
        return "CPU"
    except (AttributeError, cv2.error):
        return "CPU"

