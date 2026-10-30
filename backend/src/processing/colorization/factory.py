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

from typing import Dict, List, Type

from .base import BaseColorizer
from .models.zhang_caffe import ZhangCaffeColorizer


class ColorizerFactory:
    """Registry and factory for discovering and instantiating colorization models."""

    _registry: Dict[str, Type[BaseColorizer]] = {}
    _instances: Dict[str, BaseColorizer] = {}

    @classmethod
    def register(
        cls,
        name: str,
        colorizer_class: Type[BaseColorizer],
        allow_override: bool = False,
    ) -> None:
        """Register a colorizer model class under a unique identifier string.

        Args:
            name:
                Unique identifier string for the model (e.g. "zhang_caffe").
            colorizer_class:
                Subclass of BaseColorizer.
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

        if name in cls._registry and not allow_override:
            raise ValueError(
                f"Model '{name}' is already registered to '{cls._registry[name].__name__}'. "
                f"Pass allow_override=True to replace it."
            )

        cls._registry[name] = colorizer_class

    @classmethod
    def get_colorizer(cls, name: str = "zhang_caffe", **kwargs) -> BaseColorizer:
        """Get or instantiate a colorizer model instance by its registered name.

        Reuses cached instances so heavy neural network weights are only loaded
        once per process lifetime.

        Args:
            name:
                Registered model identifier string.
            **kwargs:
                Optional initialization arguments passed to the model class constructor
                if a new instance is created.

        Returns:
            An initialized instance of BaseColorizer.

        Raises:
            ValueError:
                If the requested model name is not in the registry.
        """
        if name not in cls._instances:
            if name not in cls._registry:
                available = cls.list_supported_models()
                raise ValueError(
                    f"Unsupported colorization model: '{name}'. "
                    f"Available models: {available}"
                )
            # Instantiate model class and cache instance
            cls._instances[name] = cls._registry[name](**kwargs)

        return cls._instances[name]

    @classmethod
    def list_supported_models(cls) -> List[str]:
        """Return a sorted list of all currently registered model identifiers."""
        return sorted(list(cls._registry.keys()))

    @classmethod
    def clear_instances(cls) -> None:
        """Clear cached model instances (primarily used in testing)."""
        cls._instances.clear()

    @classmethod
    def reset_registry(cls) -> None:
        """Reset the registry to default built-in models."""
        cls._registry.clear()
        cls._instances.clear()
        cls._register_defaults()

    @classmethod
    def _register_defaults(cls) -> None:
        """Register default built-in models."""
        cls.register("zhang_caffe", ZhangCaffeColorizer, allow_override=True)


# Register built-in default models on import
ColorizerFactory._register_defaults()

