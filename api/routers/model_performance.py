"""
api/routers/model_performance.py
------------------------------------
Read-only exposure of the same artifacts/metrics.json,
artifacts/metrics_regression.json, model_info*.json files
app/pages/Model_Performance.py already reads via ModelRegistry -
routed through the shared ModelManager singleton (models/model_manager
.py) rather than reading the files a second time here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies.services import get_model_manager
from api.schemas.model_performance import ModelPerformanceResponse, TaskPerformanceResponse
from models.model_manager import ModelManager

router = APIRouter(prefix="/model-performance", tags=["Model Performance"])


@router.get(
    "", response_model=ModelPerformanceResponse,
    summary="Classification + regression model metrics and metadata, as saved at training time",
)
def get_model_performance(model_manager: ModelManager = Depends(get_model_manager)) -> ModelPerformanceResponse:
    clf = model_manager.classification_registry
    reg = model_manager.regression_registry
    return ModelPerformanceResponse(
        classification=TaskPerformanceResponse(model_name=clf.model_name, model_info=clf.model_info, metrics=clf.metrics),
        regression=TaskPerformanceResponse(model_name=reg.model_name, model_info=reg.model_info, metrics=reg.metrics),
    )
