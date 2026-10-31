"""Module: model_service.py

Purpose:
Application service for inspecting and managing AI colorization model lifecycle.

Responsibilities:
- Check physical presence of model asset files on disk.
- Query ColorizerFactory for model initialization state.
- Return structured ModelStatusResponse without triggering heavy file downloads.
- Provide singleton access to the active BaseColorizer instance.

Dependencies:
- backend.src.core.config.settings
- backend.src.processing.colorization.factory.ColorizerFactory
- backend.src.processing.colorization.base.BaseColorizer
- backend.src.schemas.common.ModelStatusResponse
"""

from typing import List, Optional

from backend.src.core.config import settings
from backend.src.core.exceptions import ModelUnavailableError, UnsupportedColorizationModelError
from backend.src.processing.colorization.base import BaseColorizer
from backend.src.processing.colorization.factory import ColorizerFactory
from backend.src.processing.restoration.super_resolution import (
    is_model_file_present,
    is_model_loaded,
)
from backend.src.schemas.common import (
    ModelRegistryItem,
    ModelRegistryListResponse,
    ModelStatusResponse,
)


class ModelService:
    """Manages AI model availability and provides access to colorizer instances."""

    def __init__(self):
        self._default_model = "zhang_caffe"

    def get_model_status(self, model_name: Optional[str] = None) -> ModelStatusResponse:
        """Report model asset availability and initialization state on disk.

        Does NOT download weights or perform heavy model loading operations.

        Args:
            model_name:
                Name of model to inspect ('zhang_caffe', 'fsrcnn_x2', 'fsrcnn_x4').
                Defaults to 'zhang_caffe'.

        Returns:
            ModelStatusResponse indicating presence, loading state, and readiness.
        """
        name = (model_name or self._default_model).lower().strip()

        # Handle LaMa inpainting model
        if name in ("lama", "lama_inpaint"):
            lama_path = settings.MODEL_DIR / "lama_fp32.onnx" if hasattr(settings, "MODEL_DIR") else Path("model/lama_fp32.onnx")
            files_present = lama_path.is_file()
            from backend.src.processing.restoration.inpainter_lama import LaMaInpainter
            loaded = LaMaInpainter.get_instance().is_loaded

            detail = (
                "LaMa ONNX model loaded and ready for deep neural inpainting."
                if loaded
                else "LaMa ONNX model weights present on disk; loads lazily on first inpaint request."
                if files_present
                else "LaMa ONNX model file 'lama_fp32.onnx' missing from disk."
            )
            return ModelStatusResponse(
                model_name="lama",
                files_available=files_present,
                is_loaded=loaded,
                ready_for_inference=files_present,
                is_default=False,
                detail=detail,
            )

        # Handle Real-ESRGAN super-resolution model
        if name in ("realesrgan", "realesrgan_x4"):
            re_path = Path("model/realesrgan-x4plus.onnx")
            files_present = re_path.is_file()
            from backend.src.processing.restoration.sr_realesrgan import RealESRGANUpscaler
            loaded = RealESRGANUpscaler.get_instance().is_loaded

            detail = (
                "Real-ESRGAN x4plus loaded in memory and ready for inference."
                if loaded
                else "Real-ESRGAN x4plus weights present on disk; loads lazily on request."
                if files_present
                else "Real-ESRGAN weight file 'realesrgan-x4plus.onnx' missing from disk."
            )
            return ModelStatusResponse(
                model_name="realesrgan",
                files_available=files_present,
                is_loaded=loaded,
                ready_for_inference=files_present,
                is_default=False,
                detail=detail,
            )

        # Handle super-resolution models
        if name in ("fsrcnn_x2", "fsrcnn_x4"):
            scale = 2 if name == "fsrcnn_x2" else 4
            filename = f"FSRCNN_x{scale}.pb"
            files_present = is_model_file_present(scale)
            loaded = is_model_loaded(scale)

            if not files_present:
                detail = f"Super-resolution model weight file '{filename}' is missing from disk."
            elif not loaded:
                detail = (
                    f"Model file '{filename}' is present on disk. "
                    f"Model will load into memory on first {scale}x super-resolution request."
                )
            else:
                detail = f"Super-resolution model ({name}) is loaded in memory and ready for inference."

            return ModelStatusResponse(
                model_name=name,
                files_available=files_present,
                is_loaded=loaded,
                ready_for_inference=files_present,
                is_default=False,
                detail=detail,
            )

        # Built-in or registered colorization models
        if not ColorizerFactory.is_registered(name):
            return ModelStatusResponse(
                model_name=name,
                files_available=False,
                is_loaded=False,
                ready_for_inference=False,
                is_default=False,
                detail=f"Model '{name}' is not registered in the colorization registry.",
            )

        meta = ColorizerFactory.get_metadata(name)

        if name == "zhang_caffe":
            files_present = (
                settings.PROTOTXT_PATH.is_file()
                and settings.MODEL_PATH.is_file()
                and settings.POINTS_PATH.is_file()
            )
            is_loaded = False
            if name in ColorizerFactory._instances:
                is_loaded = ColorizerFactory._instances[name].is_loaded

            ready = files_present
            if not files_present:
                missing = [
                    p.name
                    for p in (settings.PROTOTXT_PATH, settings.MODEL_PATH, settings.POINTS_PATH)
                    if not p.is_file()
                ]
                detail = f"Model weight files missing from disk: {', '.join(missing)}."
            elif not is_loaded:
                detail = "Model files are present on disk. Model will load into memory on first colorization request."
            else:
                detail = "Model is loaded in memory and ready for inference."

            return ModelStatusResponse(
                model_name=name,
                files_available=files_present,
                is_loaded=is_loaded,
                ready_for_inference=ready,
                is_default=meta.is_default,
                detail=detail,
                metadata=meta.to_dict(),
            )

        # Custom registered colorizer
        is_loaded = False
        files_present = False
        if name in ColorizerFactory._instances:
            inst = ColorizerFactory._instances[name]
            is_loaded = inst.is_loaded
            files_present = inst.are_assets_present()

        return ModelStatusResponse(
            model_name=name,
            files_available=files_present,
            is_loaded=is_loaded,
            ready_for_inference=files_present,
            is_default=meta.is_default,
            detail=f"Custom model '{name}' registered in colorizer registry.",
            metadata=meta.to_dict(),
        )

    def list_registered_models(self) -> ModelRegistryListResponse:
        """Discover and list all registered colorization models with verified status and metadata."""
        items: List[ModelRegistryItem] = []
        for name in ColorizerFactory.list_supported_models():
            meta = ColorizerFactory.get_metadata(name)
            files_present = False
            is_loaded = False

            if name == "zhang_caffe":
                files_present = (
                    settings.PROTOTXT_PATH.is_file()
                    and settings.MODEL_PATH.is_file()
                    and settings.POINTS_PATH.is_file()
                )
                if name in ColorizerFactory._instances:
                    is_loaded = ColorizerFactory._instances[name].is_loaded
            else:
                if name in ColorizerFactory._instances:
                    inst = ColorizerFactory._instances[name]
                    files_present = inst.are_assets_present()
                    is_loaded = inst.is_loaded

            items.append(
                ModelRegistryItem(
                    model_id=meta.model_id,
                    display_name=meta.display_name,
                    architecture=meta.architecture,
                    authors=meta.authors,
                    publication=meta.publication,
                    model_format=meta.model_format,
                    supported_task=meta.supported_task,
                    is_default=meta.is_default,
                    files_available=files_present,
                    is_loaded=is_loaded,
                    ready_for_inference=files_present,
                    supported_parameters=meta.supported_parameters,
                    runtime_requirements=meta.runtime_requirements,
                    description=meta.description,
                )
            )

        return ModelRegistryListResponse(
            default_model=ColorizerFactory.get_default_model(),
            models=items,
        )

    def get_colorizer(self, model_name: Optional[str] = None) -> BaseColorizer:
        """Retrieve the colorizer instance from ColorizerFactory.

        Args:
            model_name:
                Identifier of the requested model.

        Returns:
            BaseColorizer instance.

        Raises:
            ModelUnavailableError:
                If required model files are missing from disk.
        """
        name = model_name or self._default_model
        status = self.get_model_status(name)
        if not status.files_available:
            raise ModelUnavailableError(
                f"Colorization model '{name}' cannot be loaded. {status.detail}"
            )

        colorizer = ColorizerFactory.get_colorizer(name)
        if not colorizer.is_loaded:
            colorizer.load_model()
        return colorizer

