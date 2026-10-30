"""AI Colorization subpackage.

Provides:
- BaseColorizer abstract strategy interface (base.py)
- ColorizerFactory registry and factory (factory.py)
- ZhangCaffeColorizer implementation (models/zhang_caffe.py)
"""

from .base import BaseColorizer
from .factory import ColorizerFactory
from .models.zhang_caffe import ZhangCaffeColorizer, colorize_image, load_caffe_model

__all__ = [
    "BaseColorizer",
    "ColorizerFactory",
    "ZhangCaffeColorizer",
    "load_caffe_model",
    "colorize_image",
]

