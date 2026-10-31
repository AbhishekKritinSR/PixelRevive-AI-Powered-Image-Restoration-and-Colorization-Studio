"""Module: factory.py

Purpose:
Provides a centralized registry and factory pattern for discovering,
instantiating, and reusing AI colorization models.

Responsibilities:
- Register supported BaseColorizer implementations by unique string identifiers.
- Validate that registered classes conform to the BaseColorizer interface.
- Prevent unintended duplicate class registrations.
- Instantiate and cache singleton model instances to prevent repeatedly loading
  heavy weights into memory.
- Provide discovery of all currently registered model identifiers.
- Raise clear, actionable exceptions when an unsupported model is requested.

Usage:
    # Registering a model:
    ColorizerFactory.register("zhang_caffe", ZhangCaffeColorizer)

    # Obtaining a model instance:
    colorizer = ColorizerFactory.get_colorizer("zhang_caffe")
    result = colorizer.colorize(image)

Dependencies:
- .base.BaseColorizer
- .models.zhang_caffe.ZhangCaffeColorizer

This module does not:
- Execute neural network inferences directly.
- Download weights or manipulate image arrays.
"""

import threading
from typing import Dict, List, Optional, Type

from backend.src.core.exceptions import UnsupportedColorizationModelError
from .base import BaseColorizer
from .metadata import ColorizerMetadata, ZHANG_CAFFE_METADATA
from .models.zhang_caffe import ZhangCaffeColorizer


class ColorizerFactory:
    """Registry and factory for discovering, instantiating, and inspecting colorization models."""

    _registry: Dict[str, Type[BaseColorizer]] = {}
    _instances: Dict[str, BaseColorizer] = {}
    _metadata: Dict[str, ColorizerMetadata] = {}
    _default_model: str = "zhang_caffe"
    _lock = threading.RLock()

    @classmethod
    def register(
        cls,
        name: str,
        colorizer_class: Type[BaseColorizer],
        metadata: Optional[ColorizerMetadata] = None,
        allow_override: bool = False,
    ) -> None:
        """Register a colorizer model class under a unique identifier string with structured metadata.

        Args:
            name:
                Unique identifier string for the model (e.g. "zhang_caffe").
            colorizer_class:
                Subclass of BaseColorizer.
            metadata:
                Optional ColorizerMetadata descriptor. If omitted, extracted from
                colorizer_class.metadata or constructed as a fallback descriptor.
            allow_override:
                Whether to allow replacing an existing registration. Default is False.

        Raises:
            TypeError:
                If colorizer_class is not a subclass of BaseColorizer.
            ValueError:
                If name is empty or already registered and allow_override is False.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Model registration name must be a non-empty string.")

        if not isinstance(colorizer_class, type) or not issubclass(colorizer_class, BaseColorizer):
            raise TypeError(
                f"Class '{colorizer_class.__name__}' must be a subclass of BaseColorizer."
            )

        with cls._lock:
            if name in cls._registry and not allow_override:
                raise ValueError(
                    f"Model '{name}' is already registered to '{cls._registry[name].__name__}'. "
                    f"Pass allow_override=True to replace it."
                )

            cls._registry[name] = colorizer_class

            # Determine structured metadata
            meta = metadata
            if meta is None:
                meta = getattr(colorizer_class, "metadata", None)
            if meta is None:
                meta = ColorizerMetadata(
                    model_id=name,
                    display_name=name,
                    architecture="Custom Architecture",
                    authors="Unknown",
                    publication="N/A",
                    model_format="Custom",
                    is_default=(name == cls._default_model),
                )
            cls._metadata[name] = meta

    @classmethod
    def get_colorizer(cls, name: str = "zhang_caffe", **kwargs) -> BaseColorizer:
        """Get or instantiate a colorizer model instance by its registered name.

        Reuses cached singleton instances in a thread-safe manner so heavy neural network
        weights are only loaded once per process lifetime.

        Args:
            name:
                Registered model identifier string.
            **kwargs:
                Optional initialization arguments passed to the model class constructor
                if a new instance is created.

        Returns:
            An initialized instance of BaseColorizer.

        Raises:
            UnsupportedColorizationModelError:
                If the requested model name is not in the registry.
        """
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    if name not in cls._registry:
                        available = cls.list_supported_models()
                        raise UnsupportedColorizationModelError(
                            f"Unsupported colorization model: '{name}'. "
                            f"Available models: {available}"
                        )
                    # Instantiate model class and cache instance
                    cls._instances[name] = cls._registry[name](**kwargs)

        return cls._instances[name]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Return True if model name is registered, False otherwise."""
        return name in cls._registry

    @classmethod
    def get_default_model(cls) -> str:
        """Return identifier of the default colorization model."""
        return cls._default_model

    @classmethod
    def get_metadata(cls, name: str) -> ColorizerMetadata:
        """Retrieve structured metadata for a registered model.

        Raises:
            UnsupportedColorizationModelError:
                If model is not registered.
        """
        if name not in cls._registry:
            available = cls.list_supported_models()
            raise UnsupportedColorizationModelError(
                f"Unsupported colorization model: '{name}'. "
                f"Available models: {available}"
            )
        return cls._metadata[name]

    @classmethod
    def list_supported_models(cls) -> List[str]:
        """Return a sorted list of all currently registered model identifiers."""
        return sorted(list(cls._registry.keys()))

    @classmethod
    def list_models_metadata(cls) -> List[ColorizerMetadata]:
        """Return structured metadata for all registered models."""
        return [cls._metadata[name] for name in cls.list_supported_models() if name in cls._metadata]

    @classmethod
    def clear_instances(cls) -> None:
        """Clear cached model instances (primarily used in testing)."""
        with cls._lock:
            cls._instances.clear()

    @classmethod
    def reset_registry(cls) -> None:
        """Reset the registry to default built-in models."""
        with cls._lock:
            cls._registry.clear()
            cls._instances.clear()
            cls._metadata.clear()
            cls._register_defaults()

    @classmethod
    def _register_defaults(cls) -> None:
        """Register default built-in models."""
        cls.register(
            "zhang_caffe",
            ZhangCaffeColorizer,
            metadata=ZHANG_CAFFE_METADATA,
            allow_override=True,
        )


# Register built-in default models on import
ColorizerFactory._register_defaults()

