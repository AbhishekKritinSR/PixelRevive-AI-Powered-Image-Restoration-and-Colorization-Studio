"""API v1 endpoints subpackage."""

from .batch import router as batch_router
from .health import router as health_router
from .models import router as models_router
from .restoration import router as restoration_router

__all__ = [
    "health_router",
    "models_router",
    "restoration_router",
    "batch_router",
]

