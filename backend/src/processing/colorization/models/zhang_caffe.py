"""Module: zhang_caffe.py

Purpose:
Encapsulates the Zhang, Isola, and Efros (ECCV 2016) Caffe deep convolutional
colorization network using OpenCV's DNN inference engine.

Responsibilities:
- Validate model assets on disk (prototxt, caffemodel weights, cluster centers).
- Automatically download model weights on first use if missing.
- Load Caffe architecture into an OpenCV cv2.dnn.Net computational graph.
- Inject empirical color cluster coordinates (pts_in_hull.npy) into the class8_ab layer.
- Inject temperature scaling bias (2.606) into the conv8_313_rh layer.
- Transform images into CIE LAB color space and extract normalized L channel.
- Execute forward pass to obtain annealed-mean chrominance distribution.
- Upsample ab predictions to original image resolution.
- Recombine predicted ab channels with uncorrupted full-resolution L channel.
- Apply defensive range clipping to [0.0, 1.0] and gamma saturation boost.

Inputs:
- image: 3-channel BGR uint8 NumPy array with shape (H, W, 3).

Outputs:
- Colorized 3-channel BGR float32 NumPy array with values in [0.0, 1.0].

Dependencies:
- cv2 (OpenCV)
- numpy
- pathlib.Path
- src.config (MODEL_PATH, PROTOTXT_PATH, POINTS_PATH, NETWORK_INPUT_SIZE,
              LAB_L_MEAN_OFFSET, NUM_AB_CLUSTERS, CLUSTER_CENTER_BIAS,
              SATURATION_GAMMA)
- src.model_downloader (ensure_model_downloaded)
- backend.src.processing.colorization.base (BaseColorizer)

This module does not:
- Train or fine-tune neural network weights.
- Alter the original Lightness channel (preserving sharpness and contrast).
- Depend on heavyweight frameworks like Caffe, PyTorch, or TensorFlow.
"""

from pathlib import Path
import threading
from typing import Optional

import cv2
import numpy as np

from backend.src.core.exceptions import InvalidRenderFactorError
from backend.src.processing.colorization.base import BaseColorizer
from backend.src.processing.colorization.metadata import ZHANG_CAFFE_METADATA
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
from src.model_downloader import ensure_model_downloaded


def validate_render_factor(render_factor: int) -> int:
    """Validate that render_factor is an integer within [MIN_RENDER_FACTOR, MAX_RENDER_FACTOR].

    Args:
        render_factor:
            Integer render factor. Factor 14 corresponds to native 224x224.

    Returns:
        Validated render factor integer.

    Raises:
        InvalidRenderFactorError:
            If render_factor is not an integer or is outside [10, 40].
    """
    if isinstance(render_factor, bool) or not isinstance(render_factor, int):
        raise InvalidRenderFactorError(
            f"render_factor must be an integer, got {type(render_factor).__name__}: {render_factor}"
        )
    if not (MIN_RENDER_FACTOR <= render_factor <= MAX_RENDER_FACTOR):
        raise InvalidRenderFactorError(
            f"render_factor ({render_factor}) is outside valid range [{MIN_RENDER_FACTOR}, {MAX_RENDER_FACTOR}]. "
            f"Factor {DEFAULT_RENDER_FACTOR} corresponds to native 224x224."
        )
    return render_factor


def load_caffe_model(
    prototxt_path: Path = PROTOTXT_PATH,
    model_path: Path = MODEL_PATH,
    points_path: Path = POINTS_PATH,
) -> cv2.dnn.Net:
    """Load the Caffe colorization network and inject cluster centers into network layers.

    Args:
        prototxt_path:
            Path to the Caffe deploy prototxt graph definition.
        model_path:
            Path to the binary caffemodel weights.
        points_path:
            Path to the pts_in_hull.npy file containing 313 quantized (a, b) cluster points.

    Returns:
        Loaded and configured cv2.dnn.Net instance ready for inference.

    Raises:
        FileNotFoundError:
            If any of the required model files are missing from disk.
    """
    # Attempt automatic download of large pretrained weights if missing
    if not model_path.is_file():
        ensure_model_downloaded()

    missing = [p for p in (prototxt_path, model_path, points_path) if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing colorization model file(s): "
            + ", ".join(str(p) for p in missing)
            + ". See the README's 'Model Setup' section for download instructions."
        )

    # Initialize neural network from Caffe description and weights
    net = cv2.dnn.readNetFromCaffe(
        str(prototxt_path),
        str(model_path),
    )

    # Load 313 quantized (a, b) color cluster centers (shape: 313, 2)
    pts = np.load(points_path)

    # Locate the target layers within the Caffe computation graph
    class8 = net.getLayerId("class8_ab")
    conv8 = net.getLayerId("conv8_313_rh")

    # Reshape points to (2, 313, 1, 1) to act as 1x1 convolution kernels
    # that map 313 class probabilities into expected (a, b) coordinate values
    pts = pts.transpose().reshape(2, NUM_AB_CLUSTERS, 1, 1)

    # Inject cluster coordinates as weights into the decoding layer
    net.getLayer(class8).blobs = [pts.astype("float32")]

    # Inject temperature scaling factor (1 / T = 2.606, T ~= 0.38) into scale layer
    net.getLayer(conv8).blobs = [
        np.full([1, NUM_AB_CLUSTERS], CLUSTER_CENTER_BIAS, dtype="float32")
    ]

    return net


def colorize_image(
    image: np.ndarray,
    net: cv2.dnn.Net,
    render_factor: int = DEFAULT_RENDER_FACTOR,
    saturation_gamma: float = SATURATION_GAMMA,
    saturation: float = 0.85,
    color_temperature: float = 0.0,
    edge_refinement: bool = True,
    shadow_attenuation: bool = True,
    color_saturation: Optional[float] = None,
    **kwargs,
) -> np.ndarray:
    """Colorize a BGR uint8 image using a loaded Caffe colorization network.

    The colorization process:
    1. Scales BGR to [0.0, 1.0] and transforms to CIE LAB.
    2. Isolates the L (Lightness) channel, resizes to (render_factor*16)x(render_factor*16),
       and subtracts 50.0 (mean offset). Native resolution is 224x224 (render_factor=14).
    3. Feeds L into the network to predict the probability distribution over 313 (a, b) bins.
    4. Computes the annealed mean of (a, b) chrominance channels.
    5. Upsamples predicted ab channels to the original image dimensions.
    6. Refines chrominance boundaries via guided filtering aligned to original L structure.
    7. Adjusts saturation and chromatic balance to eliminate oversaturated red/yellow cast.
    8. Attenuates chromatic noise in deep shadows and highlights.
    9. Recombines original uncompromised L with refined ab channels.
    10. Converts reconstructed LAB to BGR and clamps to [0.0, 1.0].

    Args:
        image:
            Input BGR image as a uint8 NumPy array of shape (height, width, 3).
        net:
            Configured cv2.dnn.Net instance returned by `load_caffe_model()`.
        render_factor:
            Integer render factor between 10 and 40 (default 14 -> 224x224).
        saturation_gamma:
            Gamma curve power applied to BGR output (default 0.9).
        saturation:
            Chroma saturation factor in LAB space (default 0.85 for natural tones).
        color_temperature:
            Temperature bias factor (-1.0 to 1.0, default 0.0).
        edge_refinement:
            Whether to align chrominance edges to luminance boundaries via guided filter.
        shadow_attenuation:
            Whether to desaturate deep shadows and specular highlights.

    Returns:
        Colorized BGR image as a float32 NumPy array in range [0.0, 1.0].
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a valid NumPy array.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"Expected a 3-channel color image (H, W, 3), but got shape {image.shape}."
        )

    if color_saturation is not None:
        saturation = color_saturation

    # Validate render factor parameter
    validated_factor = validate_render_factor(render_factor)
    network_input_size = validated_factor * 16

    # Normalize image to float32 [0.0, 1.0]
    scaled = image.astype("float32") / 255.0

    # Convert to CIE LAB color space
    lab = cv2.cvtColor(scaled, cv2.COLOR_BGR2LAB)

    # Extract Lightness channel (L: range 0.0 to 100.0)
    L = lab[:, :, 0]

    # Resize L channel to tuned network input dimension (default 224x224)
    L_resized = cv2.resize(L, (network_input_size, network_input_size))

    # Mean-center L channel before feeding into CNN
    L_resized -= LAB_L_MEAN_OFFSET

    # Construct 4D input blob (1, 1, H, W) and set network input
    net.setInput(cv2.dnn.blobFromImage(L_resized))

    # Forward pass: outputs expected (a, b) chrominance channels
    ab = net.forward()[0, :, :, :].transpose((1, 2, 0))

    # Resize predicted ab channels back to original image dimensions
    ab = cv2.resize(ab, (image.shape[1], image.shape[0]))

    # Resize original L channel to original image dimensions (safeguard)
    L = cv2.resize(L, (image.shape[1], image.shape[0]))

    # 1. Edge-Preserving Chrominance Alignment (Guided Filtering)
    if edge_refinement and hasattr(cv2, "ximgproc") and hasattr(cv2.ximgproc, "guidedFilter"):
        try:
            L_guide = np.clip(L * 2.55, 0, 255).astype(np.uint8)
            ab_a = np.ascontiguousarray(ab[:, :, 0], dtype=np.float32)
            ab_b = np.ascontiguousarray(ab[:, :, 1], dtype=np.float32)
            a_ref = cv2.ximgproc.guidedFilter(guide=L_guide, src=ab_a, radius=6, eps=100.0)
            b_ref = cv2.ximgproc.guidedFilter(guide=L_guide, src=ab_b, radius=6, eps=100.0)
            ab = np.stack([a_ref, b_ref], axis=2)
        except Exception:
            pass

    # 2. Temperature and White Balance Compensation (positive = warm/yellow-red, negative = cool/blue)
    if color_temperature != 0.0:
        ab[:, :, 1] += float(color_temperature * 4.0)
        ab[:, :, 0] += float(color_temperature * 1.5)

    # 3. Saturation Tuning in CIE LAB Space
    if saturation != 1.0 and saturation >= 0.0:
        ab = ab * float(saturation)

    # 4. Shadow and Highlight Desaturation to Prevent Chromatic Blotches
    if shadow_attenuation:
        fade = np.clip((L - 8.0) / 12.0, 0.0, 1.0) * np.clip((95.0 - L) / 8.0, 0.0, 1.0)
        ab = ab * fade[:, :, np.newaxis]

    # Recombine original full-resolution L with CNN-predicted ab channels
    colorized = np.concatenate((L[:, :, np.newaxis], ab), axis=2)

    # Convert reconstructed LAB -> BGR
    colorized = cv2.cvtColor(colorized, cv2.COLOR_LAB2BGR)

    # Defensive clipping: LAB -> BGR can produce values slightly outside [0.0, 1.0]
    colorized = np.clip(colorized, 0, 1)

    # Saturation boost via gamma power curve if specified
    if saturation_gamma != 1.0:
        colorized = np.power(colorized, saturation_gamma)

    return colorized


class ZhangCaffeColorizer(BaseColorizer):
    """Concrete BaseColorizer implementation for the Zhang et al. (ECCV 2016) Caffe model."""

    metadata = ZHANG_CAFFE_METADATA

    def __init__(
        self,
        prototxt_path: Path = PROTOTXT_PATH,
        model_path: Path = MODEL_PATH,
        points_path: Path = POINTS_PATH,
    ):
        self.prototxt_path = prototxt_path
        self.model_path = model_path
        self.points_path = points_path
        self._net: Optional[cv2.dnn.Net] = None
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return "zhang_caffe"

    @property
    def is_loaded(self) -> bool:
        return self._net is not None

    def are_assets_present(self) -> bool:
        """Check whether all three Caffe asset files exist on disk."""
        return (
            self.prototxt_path.is_file()
            and self.model_path.is_file()
            and self.points_path.is_file()
        )

    def load_model(self) -> None:
        """Load the Caffe network into memory with thread-safe locking."""
        if not self.is_loaded:
            with self._lock:
                if not self.is_loaded:
                    self._net = load_caffe_model(
                        self.prototxt_path,
                        self.model_path,
                        self.points_path,
                    )

    def colorize(
        self,
        image_bgr: np.ndarray,
        net: Optional[cv2.dnn.Net] = None,
        render_factor: int = DEFAULT_RENDER_FACTOR,
        **kwargs,
    ) -> np.ndarray:
        """Colorize image using loaded network or explicitly provided network instance."""
        target_net = net if net is not None else self._net
        if target_net is None:
            self.load_model()
            target_net = self._net
        return colorize_image(image_bgr, target_net, render_factor=render_factor, **kwargs)

