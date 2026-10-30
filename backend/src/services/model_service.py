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

from typing import Optional

from backend.src.core.config import settings
from backend.src.core.exceptions import ModelUnavailableError
from backend.src.processing.colorization.base import BaseColorizer
from backend.src.processing.colorization.factory import ColorizerFactory
from backend.src.schemas.common import ModelStatusResponse


class ModelService:
    """Manages AI model availability and provides access to colorizer instances."""

    def __init__(self):
        self._default_model = "zhang_caffe"

    def get_model_status(self, model_name: Optional[str] = None) -> ModelStatusResponse:
        """Report model asset availability and initialization state on disk.

        Does NOT download weights or perform network operations.

        Args:
            model_name:
                Name of model to inspect (default: 'zhang_caffe').

        Returns:
            ModelStatusResponse indicating presence, loading state, and readiness.
        """
        name = model_name or self._default_model
        files_present = (
            settings.PROTOTXT_PATH.is_file()
            and settings.MODEL_PATH.is_file()
            and settings.POINTS_PATH.is_file()
        )

        # Check if the singleton instance is loaded in ColorizerFactory
        is_loaded = False
        if name in ColorizerFactory._instances:
            is_loaded = ColorizerFactory._instances[name].is_loaded

        ready = files_present

        detail = None
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
            detail=detail,
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

