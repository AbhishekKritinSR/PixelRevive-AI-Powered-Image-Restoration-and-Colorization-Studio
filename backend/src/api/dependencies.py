"""Module: dependencies.py

Purpose:
FastAPI dependency injection providers for service singletons.

Responsibilities:
- Provide singletons for ModelService, RestorationService, and BatchService.
- Allow tests to easily override service dependencies using app.dependency_overrides.
"""

from functools import lru_cache

from backend.src.services.analysis_service import AnalysisService
from backend.src.services.batch_service import BatchService
from backend.src.services.model_service import ModelService
from backend.src.services.quality_service import QualityService
from backend.src.services.restoration_service import RestorationService


@lru_cache()
def get_analysis_service() -> AnalysisService:
    """Return cached singleton instance of AnalysisService."""
    return AnalysisService()


@lru_cache()
def get_quality_service() -> QualityService:
    """Return cached singleton instance of QualityService."""
    return QualityService()


@lru_cache()
def get_model_service() -> ModelService:
    """Return cached singleton instance of ModelService."""
    return ModelService()


def get_restoration_service() -> RestorationService:
    """Return an initialized RestorationService instance."""
    return RestorationService(model_service=get_model_service())


def get_batch_service() -> BatchService:
    """Return an initialized BatchService instance."""
    return BatchService(restoration_service=get_restoration_service())

