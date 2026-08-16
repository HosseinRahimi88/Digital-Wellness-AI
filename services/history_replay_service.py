"""
History Replay
--------------
Turns a stored history snapshot back into the objects the normal
prediction pipeline produces, so a past day can be reopened on the same
result screen it was first shown on.

Why replay instead of re-predict
--------------------------------
Re-running the model would be the obvious shortcut and it would be
wrong. The classifier is given the user's earlier check-ins to build
trend features from, so predicting the 3rd of the month *today* uses
history that did not exist on the 3rd - it would quietly produce a
different number than the one already sitting in that day's heatmap
cell. Reopening a day has to show the score the user was actually
given, so the model's own output is read back from storage and never
recomputed.

What is recomputed, deliberately, is everything downstream of the model:
recommendations, dimension breakdown, confidence wording, the OOD check
and tone framing are all derived from (inputs, model output) by
`build_predict_response`, and running them again keeps a reopened day
identical in shape to a fresh one instead of forking a second renderer.
It also means a day reopened after the user changed their tone or muted
a recommendation category respects that choice.

Entries written before snapshots existed simply have none. They are
reported as un-reopenable rather than reconstructed from the ~20
summary fields those entries do carry - a check-in rebuilt from a third
of its inputs is a different check-in, and showing it as the user's day
would be a fabrication.
"""

from __future__ import annotations

from typing import Any

from models.schemas import PredictionResult
from services.shap_service import SHAPFeature
from services.uncertainty_service import UncertaintyResult

SUPPORTED_SNAPSHOT_VERSIONS = frozenset({1})


class SnapshotUnavailableError(Exception):
    """Raised when a history entry cannot be reopened faithfully.

    `reason` is a stable machine-readable code, so the caller can tell
    the user which of the two cases they hit instead of one vague
    'not found'.
    """

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


class _ReplayedValidation:
    """The `validation` shape `build_predict_response` reads.

    Only `.cleaned_data` is touched there. The stored inputs already
    passed ValidationService when they were first submitted, so they are
    presented as valid rather than re-derived - re-validating could
    reject a day that was legitimately recorded under earlier bounds and
    make the user's own past disappear.
    """

    __slots__ = ("cleaned_data", "is_valid", "errors")

    def __init__(self, cleaned_data: dict[str, Any]) -> None:
        self.cleaned_data = cleaned_data
        self.is_valid = True
        self.errors = {}


def snapshot_of(entry: dict[str, Any]) -> dict[str, Any]:
    """The usable snapshot on `entry`, or raise explaining why not."""
    snapshot = entry.get("snapshot")
    if not isinstance(snapshot, dict):
        raise SnapshotUnavailableError(
            "no_snapshot",
            "This day was recorded before full check-in detail was kept, "
            "so only its summary is available.",
        )

    version = snapshot.get("version")
    if version not in SUPPORTED_SNAPSHOT_VERSIONS:
        raise SnapshotUnavailableError(
            "unsupported_snapshot_version",
            f"This day was stored in an unsupported format (version {version!r}).",
        )

    inputs = snapshot.get("inputs")
    model_output = snapshot.get("model_output")
    if not isinstance(inputs, dict) or not inputs or not isinstance(model_output, dict):
        raise SnapshotUnavailableError(
            "incomplete_snapshot",
            "This day's stored detail is incomplete, so it cannot be reopened accurately.",
        )
    return snapshot


def replay(entry: dict[str, Any]) -> tuple[_ReplayedValidation, PredictionResult]:
    """Rebuild the `(validation, result)` pair `build_predict_response` takes.

    Raises `SnapshotUnavailableError` when the entry cannot be reopened.
    """
    snapshot = snapshot_of(entry)
    inputs = dict(snapshot["inputs"])
    out = snapshot["model_output"]

    shap_features = [
        SHAPFeature(
            feature=f.get("feature"),
            value=f.get("value"),
            shap_value=f.get("shap_value", 0.0),
            abs_shap=f.get("abs_shap", 0.0),
            direction=f.get("direction", ""),
            score=f.get("score", 0.0),
        )
        for f in (out.get("shap_features") or [])
        if isinstance(f, dict)
    ]

    uncertainty = None
    raw_uncertainty = out.get("uncertainty")
    if isinstance(raw_uncertainty, dict):
        # Only the fields UncertaintyResult declares - a snapshot written
        # by a later version with extra keys must not blow up here.
        known = {f for f in UncertaintyResult.__slots__}
        uncertainty = UncertaintyResult(
            **{k: v for k, v in raw_uncertainty.items() if k in known}
        )

    result = PredictionResult(
        prediction=out.get("prediction") or "",
        confidence=out.get("confidence"),
        probabilities=dict(out.get("probabilities") or {}),
        regression_score=out.get("regression_score"),
        shap_features=shap_features,
        model_name=out.get("model_name") or "",
        prediction_time_ms=out.get("prediction_time_ms") or 0.0,
        timestamp=out.get("timestamp"),
        uncertainty=uncertainty,
    )
    return _ReplayedValidation(inputs), result
