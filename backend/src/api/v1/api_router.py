"""Module: api_router.py

Purpose:
Aggregates and mounts all version 1 (v1) API routers under a single APIRouter.
"""

from fastapi import APIRouter

from .endpoints.analysis import router as analysis_router
from .endpoints.batch import router as batch_router
from .endpoints.health import router as health_router
from .endpoints.models import router as models_router
from .endpoints.quality import router as quality_router
from .endpoints.restoration import router as restoration_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(models_router, tags=["Models"])
api_router.include_router(restoration_router, tags=["Restoration"])
api_router.include_router(analysis_router, tags=["Restoration"])
api_router.include_router(batch_router, tags=["Restoration"])
api_router.include_router(quality_router, tags=["Quality Assessment"])

