"""
api/routers/whatif.py
-------------------------
"What if I changed one thing" endpoints: a sensitivity sweep across a
single field's schema range, and a goal-seek search for the input
value that reaches a target score. Both run AdvancedWhatIfService over
the real trained model with `compute_shap=False` (these calls only
need the point prediction, not a full explanation, at every swept
value) - never a cheaper approximation of the model itself.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import get_prediction_service, get_validation_service
from api.exceptions.errors import DomainValidationError
from api.schemas.whatif import (
    GoalSeekRequest,
    GoalSeekResponse,
    SweepPointResponse,
    SweepRequest,
    SweepResponse,
)
from services.identity.account_service import Account
from services.insight.advanced_whatif_service import AdvancedWhatIfService
from services.ml.prediction_service import PredictionService
from services.ml.validation_service import ValidationService
from utils.feature_derivation import derive_features

router = APIRouter(prefix="/whatif", tags=["What-If Analysis"])


def _validated(validator: ValidationService, user_data: dict):
    """The same admission the /predict endpoint gives a day.

    These two endpoints validated `payload.user_data` RAW, while
    /predict validates `derive_features(user_data)`. The fourteen
    derived columns - total_screen_min, the five ratios, the three
    densities, fragmentation, dependence, the two baselines - are
    computed, not typed, so a caller sending the same body /predict
    accepts got back 422 "This field is required" fourteen times over
    and the simulator did nothing at all.

    It only ever LOOKED like it worked because the page happens to hold
    an already-derived payload: /history/snapshots returns cleaned data,
    and the check-in form derives client-side before POSTing. Any other
    caller - the API docs' own example, a script, a page that starts
    from raw answers - hit the wall.

    Deriving here also means a sweep can never be handed a day whose
    ratios disagree with its minutes, which is the same guarantee
    build_scenario_input() gives every swept point after this one.
    """
    validation = validator.validate(derive_features(dict(user_data)))
    if not validation.is_valid:
        raise DomainValidationError(validation.errors)
    return validation


@router.post(
    "/sweep", response_model=SweepResponse,
    summary="Predicted score/class at N evenly-spaced values of one field across its schema range",
)
def sweep_field(
    payload: SweepRequest,
    account: Account = Depends(get_current_account),
    validator: ValidationService = Depends(get_validation_service),
    predictor: PredictionService = Depends(get_prediction_service),
) -> SweepResponse:
    validation = _validated(validator, payload.user_data)

    points = AdvancedWhatIfService.sweep_field(
        validation.cleaned_data, predictor, payload.field, num_points=payload.num_points,
    )
    return SweepResponse(
        field=payload.field,
        points=[SweepPointResponse(value=p.value, score=p.score, prediction=p.prediction) for p in points],
    )


@router.post(
    "/goal-seek", response_model=GoalSeekResponse,
    summary="Grid-search one field's schema range for the value whose predicted score is closest to a target",
)
def goal_seek(
    payload: GoalSeekRequest,
    account: Account = Depends(get_current_account),
    validator: ValidationService = Depends(get_validation_service),
    predictor: PredictionService = Depends(get_prediction_service),
) -> GoalSeekResponse:
    validation = _validated(validator, payload.user_data)

    result = AdvancedWhatIfService.goal_seek(
        validation.cleaned_data, predictor, payload.field, payload.target_score,
        num_points=payload.num_points,
    )
    if result is None:
        return GoalSeekResponse(available=False)

    return GoalSeekResponse(
        available=True,
        field=result.field,
        target_score=result.target_score,
        best_value=result.best_value,
        best_score=result.best_score,
        distance=result.distance,
        reached=result.reached,
        current_value=result.current_value,
        current_score=result.current_score,
        already_there=result.already_there,
        points=[SweepPointResponse(value=p.value, score=p.score, prediction=p.prediction) for p in result.points],
    )
