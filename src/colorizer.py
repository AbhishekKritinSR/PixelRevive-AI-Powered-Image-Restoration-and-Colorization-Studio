"""CNN-based image colorization using OpenCV's dnn module.

Backward-compatibility wrapper preserving the original public interface of `src.colorizer`,
delegating to the modular implementation in `backend.src.processing.colorization`.
"""

from backend.src.processing.colorization.models.zhang_caffe import (
    colorize_image as colorize,
    load_caffe_model,
    validate_render_factor,
)
from src.config import (
    CLUSTER_CENTER_BIAS,
    DEFAULT_RENDER_FACTOR,
    LAB_L_MEAN_OFFSET,
    MAX_RENDER_FACTOR,
    MIN_RENDER_FACTOR,
    MODEL_PATH,
    NETWORK_INPUT_SIZE,
    NUM_AB_CLUSTERS,
    POINTS_PATH,
    PROTOTXT_PATH,
    SATURATION_GAMMA,
)


def load_model():
    """Load the Caffe colorization network using paths defined at module level."""
    return load_caffe_model(
        prototxt_path=PROTOTXT_PATH,
        model_path=MODEL_PATH,
        points_path=POINTS_PATH,
    )


__all__ = [
    "load_model",
    "colorize",
    "validate_render_factor",
    "PROTOTXT_PATH",
    "MODEL_PATH",
    "POINTS_PATH",
    "NETWORK_INPUT_SIZE",
    "LAB_L_MEAN_OFFSET",
    "NUM_AB_CLUSTERS",
    "CLUSTER_CENTER_BIAS",
    "SATURATION_GAMMA",
    "MIN_RENDER_FACTOR",
    "DEFAULT_RENDER_FACTOR",
    "MAX_RENDER_FACTOR",
]
