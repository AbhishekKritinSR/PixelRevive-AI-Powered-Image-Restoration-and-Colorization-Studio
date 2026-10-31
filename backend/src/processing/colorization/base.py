"""Module: base.py

Purpose:
Defines the abstract Strategy interface that all AI colorization models must implement.

Responsibilities:
- Declare the required public contract for colorization model implementations.
- Provide clear type annotations and docstrings defining expected inputs and outputs.
- Maintain independence from any specific deep learning framework or model backend.

Abstract Interface Requirements:
- load_model(): Prepare the network and weights for inference.
- colorize(image_bgr): Predict color channels and reconstruct a colorized image.
- model_name: String property returning the unique identifier of the model.
- is_loaded: Boolean property indicating whether the model is ready for inference.

This module does not:
- Implement any neural network operations.
- Depend on OpenCV DNN, PyTorch, TensorFlow, or ONNX.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

import numpy as np

if TYPE_CHECKING:
    from .metadata import ColorizerMetadata


class BaseColorizer(ABC):
    """Abstract Strategy interface for AI-based photograph colorization models.

    Subclasses encapsulate specific neural network architectures and runtimes
    (e.g. Caffe via OpenCV DNN, ONNX Runtime, OpenVINO, PyTorch) while exposing
    a consistent, predictable interface to application services and pipelines.
    """

    @abstractmethod
    def load_model(self) -> None:
        """Load network architecture and pretrained weights into memory.

        Raises:
            FileNotFoundError:
                If required model configuration or weight files are missing.
            RuntimeError:
                If the model cannot be loaded by the underlying inference engine.
        """
        pass

    @abstractmethod
    def colorize(self, image_bgr: np.ndarray, **kwargs) -> np.ndarray:
        """Colorize a BGR image using the loaded neural network model.

        Args:
            image_bgr:
                Input image as a uint8 NumPy array of shape (height, width, 3).
                May be grayscale (replicated to 3 identical channels) or color.
            **kwargs:
                Optional tuning parameters supported by the specific model
                (e.g. render_factor).

        Returns:
            Colorized image as a float32 NumPy array with shape (height, width, 3),
            with pixel intensities in the normalized range [0.0, 1.0].

        Raises:
            RuntimeError:
                If inference is attempted before `load_model()` has succeeded.
            ValueError:
                If the input image format or dimensions are invalid.
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the unique string identifier for this colorizer model."""
        pass

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Return True if model weights are loaded and ready for inference, False otherwise."""
        pass

    @classmethod
    def get_metadata(cls) -> Optional["ColorizerMetadata"]:
        """Return structured metadata descriptor for this colorizer class."""
        return getattr(cls, "metadata", None)

    def are_assets_present(self) -> bool:
        """Return True if required model asset files are physically present on disk."""
        return True

