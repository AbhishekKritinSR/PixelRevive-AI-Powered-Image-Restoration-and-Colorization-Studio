"""Module: metadata.py

Purpose:
Defines immutable structured metadata schemas and standard descriptors
for AI colorization models in PixelRevive.

Responsibilities:
- Provide a standardized, type-safe representation of model metadata (architecture,
  authors, publication, license, tuning parameters, runtime requirements).
- Supply verified metadata for the default Zhang et al. (ECCV 2016) Caffe colorizer.
- Ensure strict factual attribution without fabricated metrics or unverified benchmarks.

Dependencies:
- dataclasses (dataclass, field)
- typing (Any, Dict, Optional)
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ColorizerMetadata:
    """Structured, immutable metadata describing an AI colorization model."""

    model_id: str
    display_name: str
    architecture: str
    authors: str
    publication: str
    model_format: str
    supported_task: str = "Image Colorization"
    is_default: bool = False
    supported_parameters: Dict[str, Any] = field(default_factory=dict)
    runtime_requirements: str = "OpenCV DNN with Caffe support (CPU)"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to a serializable dictionary representation."""
        return asdict(self)


# Authoritative metadata for the built-in Zhang et al. (ECCV 2016) Caffe model
ZHANG_CAFFE_METADATA = ColorizerMetadata(
    model_id="zhang_caffe",
    display_name="Zhang et al. ECCV 2016 (Caffe)",
    architecture="Convolutional Neural Network (8-block fully convolutional CNN)",
    authors="Richard Zhang, Phillip Isola, Alexei A. Efros",
    publication="Colorful Image Colorization, ECCV 2016",
    model_format="Caffe (.prototxt graph, .caffemodel weights, .npy cluster centers)",
    supported_task="Image Colorization",
    is_default=True,
    supported_parameters={
        "render_factor": {
            "type": "int",
            "default": 14,
            "min": 10,
            "max": 40,
            "description": (
                "Colorization rendering factor controlling internal network receptive resolution "
                "(resolution = factor * 16). Factor 14 corresponds to native 224x224."
            ),
        }
    },
    runtime_requirements="OpenCV DNN with Caffe support (CPU)",
    description=(
        "Deep convolutional colorization network trained with class-rebalanced multinomial cross-entropy "
        "loss. Reconstructs CIE LAB chrominance distributions over 313 quantized color clusters using "
        "annealed-mean decoding."
    ),
)

