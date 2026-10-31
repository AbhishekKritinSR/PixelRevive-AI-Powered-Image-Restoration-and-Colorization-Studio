"""AI Colorization subpackage.

Provides:
- BaseColorizer abstract strategy interface (base.py)
- ColorizerFactory registry and factory (factory.py)
- ZhangCaffeColorizer implementation (models/zhang_caffe.py)
"""

from .base import BaseColorizer
from .factory import ColorizerFactory
from .metadata import ColorizerMetadata, ZHANG_CAFFE_METADATA
from .models.zhang_caffe import (
    ZhangCaffeColorizer,
    colorize_image,
    load_caffe_model,
    validate_render_factor,
)

__all__ = [
    "BaseColorizer",
    "ColorizerFactory",
    "ColorizerMetadata",
    "ZHANG_CAFFE_METADATA",
    "ZhangCaffeColorizer",
    "load_caffe_model",
    "colorize_image",
    "validate_render_factor",
]

