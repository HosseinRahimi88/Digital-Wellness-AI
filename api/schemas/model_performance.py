"""api/schemas/model_performance.py"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TaskPerformanceResponse(BaseModel):
    model_name: str
    model_info: dict[str, Any]
    metrics: dict[str, Any]


class HorizonResponse(BaseModel):
    """Which point in time each model is actually about.

    This is here because the app was presenting two figures with two
    different horizons as one reading. The classifier's target is
    `future_health_class_7d` - seven days out. The regressor's target is
    `health_score_0_100` - today. Nothing on a performance page should
    make a reader work that out from a column name.
    """

    classification_target: str
    classification_horizon: str          # "7_days_ahead"
    regression_target: str
    regression_horizon: str              # "today"
    # How the seven-day score band is produced, and why it is not a
    # trained regressor. Read from the calibration artifact so the page
    # cannot describe a method the code is not using.
    future_score_method: str | None = None
    future_score_why_not_a_regressor: str | None = None
    future_score_evidence: dict[str, Any] | None = None


class ModelPerformanceResponse(BaseModel):
    classification: TaskPerformanceResponse
    regression: TaskPerformanceResponse
    horizons: HorizonResponse | None = None


class FeatureCoverageResponse(BaseModel):
    field_name: str
    days: int
    # Share of this user's days falling outside the training p5-p95.
    # ~0.10 is what an in-distribution person scores, because the tails
    # hold 10% of the training population by definition.
    tail_rate: float
    band: str  # covered | thin | extrapolating
    user_median: float | None = None
    reference_median: float | None = None
    reference_low: float | None = None
    reference_high: float | None = None


class FeaturePSIResponse(BaseModel):
    field_name: str
    psi: float
    band: str  # stable | moderate | significant
    rows: int


class PopulationDriftResponse(BaseModel):
    """PSI over every stored check-in, pooled across accounts.

    Ten bucket proportions per feature describe nobody in particular,
    which is what makes it safe to return to a signed-in user - and it
    is the only form in which PSI is statistically meaningful here. One
    person's days are far narrower than 93,000 rows from thousands of
    people, so per-user PSI reads "significant shift" for ordinary
    users; see services/ml/drift_service.py.
    """

    available: bool
    reason: str  # ok | not_enough_rows | no_reference
    rows: int = 0
    overall_band: str = "stable"
    features: list[FeaturePSIResponse] = Field(default_factory=list)
    worst: FeaturePSIResponse | None = None
    min_rows: int = 0
    moderate_psi: float = 0.0
    significant_psi: float = 0.0


class DriftResponse(BaseModel):
    """Whether the models are being asked about inputs they never saw.

    Two questions, two metrics, because one metric cannot answer both:

      `you`         coverage - how much of YOUR data lands where the
                    model has none. A coverage question, so it is
                    measured as a tail rate, not as PSI.
      `population`  drift - whether the people using this app have
                    moved away from the training population. A genuine
                    distribution comparison, so PSI, pooled.
    """

    available: bool
    # ok | not_enough_days | no_reference | no_usable_fields
    reason: str
    days: int = 0
    # False below the day count where the number stops being noise.
    reliable: bool = False
    overall_band: str = "covered"
    features: list[FeatureCoverageResponse] = Field(default_factory=list)
    worst: FeatureCoverageResponse | None = None

    population: PopulationDriftResponse | None = None

    # Named rather than implied - the rule the cohort panel follows.
    reference_source: str = "none"
    reference_rows: int = 0
    min_days: int = 0
    reliable_days: int = 0
    moderate_tail_rate: float = 0.0
    significant_tail_rate: float = 0.0
    expected_tail_rate: float = 0.0
