"""
api/routers/model_performance.py
------------------------------------
Read-only exposure of the same artifacts/metrics.json,
artifacts/metrics_regression.json, model_info*.json files
legacy/streamlit_app/pages/Model_Performance.py already reads via ModelRegistry -
routed through the shared ModelManager singleton (models/model_manager
.py) rather than reading the files a second time here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import (
    get_history_service, get_history_storage_backend, get_model_manager,
)
from api.schemas.model_performance import (
    DriftResponse, FeatureCoverageResponse, FeaturePSIResponse, HorizonResponse,
    ModelPerformanceResponse, PopulationDriftResponse, TaskPerformanceResponse,
)
from services.identity.account_service import Account
from services.ml import drift_service as drift
from services.storage.base import StorageBackend
from services.insight.future_score_service import FutureScoreService
from models.model_manager import ModelManager

router = APIRouter(prefix="/model-performance", tags=["Model Performance"])


@router.get(
    "", response_model=ModelPerformanceResponse,
    summary="Classification + regression model metrics and metadata, as saved at training time",
)
def get_model_performance(model_manager: ModelManager = Depends(get_model_manager)) -> ModelPerformanceResponse:
    clf = model_manager.classification_registry
    reg = model_manager.regression_registry
    calibration = FutureScoreService.calibration_summary() or {}
    horizons = HorizonResponse(
        classification_target=str(clf.model_info.get("target_column", "")),
        classification_horizon="7_days_ahead",
        regression_target=str(reg.model_info.get("target_column", "")),
        regression_horizon="today",
        future_score_method=calibration.get("method"),
        future_score_why_not_a_regressor=calibration.get("why_not_a_regressor"),
        future_score_evidence=calibration.get("evidence"),
    )
    return ModelPerformanceResponse(
        classification=TaskPerformanceResponse(model_name=clf.model_name, model_info=clf.model_info, metrics=clf.metrics),
        regression=TaskPerformanceResponse(model_name=reg.model_name, model_info=reg.model_info, metrics=reg.metrics),
        horizons=horizons,
    )


@router.get(
    "/drift", response_model=DriftResponse,
    summary="Whether the models are being asked about inputs they were never fitted on",
)
def get_drift(
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> DriftResponse:
    """The question the rest of this page could not answer.

    Every other number here describes how the models did on their own
    held-out split, once, at training time. None of them say whether the
    rows being fed in TODAY resemble the rows they learned from - and a
    model can be 97% accurate on its test set while confidently
    extrapolating about somebody it has no basis for.

    Two metrics, because one cannot answer both questions - see
    services/ml/drift_service.py for why per-user PSI is the wrong tool
    and reads "significant" for perfectly ordinary people.
    """
    service = drift.DriftService()

    try:
        history = get_history_service(account, storage=storage)
        mine = list(history.get_all())
    except Exception:  # noqa: BLE001 - a diagnostics panel must not 500
        mine = []
    report = service.report(mine)

    # Every account's rows together. Only pooled bucket proportions come
    # back out, which describe nobody in particular - see the schema.
    try:
        # The whole store, not this user's slice - HistoryService.storage
        # is the same backend the test harness injects, so this reads
        # whatever the running deployment actually has.
        pooled = list(history.storage.read_all())
    except Exception:  # noqa: BLE001
        pooled = []
    population = service.population(pooled)

    def _coverage(item) -> FeatureCoverageResponse:
        return FeatureCoverageResponse(
            field_name=item.field_name, days=item.days, tail_rate=item.tail_rate,
            band=item.band, user_median=item.user_median,
            reference_median=item.reference_median,
            reference_low=item.reference_low, reference_high=item.reference_high,
        )

    def _psi(item) -> FeaturePSIResponse:
        return FeaturePSIResponse(
            field_name=item.field_name, psi=item.psi, band=item.band, rows=item.rows,
        )

    return DriftResponse(
        available=report.available,
        reason=report.reason,
        days=report.days,
        reliable=report.reliable,
        overall_band=report.overall_band,
        features=[_coverage(f) for f in report.features],
        worst=_coverage(report.worst) if report.worst else None,
        population=PopulationDriftResponse(
            available=population.available,
            reason=population.reason,
            rows=population.rows,
            overall_band=population.overall_band,
            features=[_psi(f) for f in population.features],
            worst=_psi(population.worst) if population.worst else None,
            min_rows=drift.MIN_POOLED_ROWS,
            moderate_psi=drift.MODERATE_PSI,
            significant_psi=drift.SIGNIFICANT_PSI,
        ),
        reference_source=service.reference_source,
        reference_rows=service.reference_rows,
        min_days=drift.MIN_DAYS,
        reliable_days=drift.RELIABLE_DAYS,
        moderate_tail_rate=drift.MODERATE_TAIL_RATE,
        significant_tail_rate=drift.SIGNIFICANT_TAIL_RATE,
        expected_tail_rate=drift.EXPECTED_TAIL_RATE,
    )
