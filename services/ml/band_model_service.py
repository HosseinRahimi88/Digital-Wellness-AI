"""Serves the personal week-band half-width.

The weekly plan's band is `the weighted mean of this week's scores +/-
a half-width`. The centre has not changed and neither has any other
plan rule; this module is only the half-width, and only when a trained
artifact is present.

Everything here is written so that a missing, stale or broken artifact
degrades to the old constant rather than to an error. `half_width()`
returns None on ANY problem, and the one caller
(services/wellness/plan_lock_service.week_band) reads None as "use
BAND_HALF_WIDTH". A user must not lose their weekly plan because a
pickle would not unpickle.

Why the model exists at all - measured on the dataset's real
per-respondent sequences, held out by respondent:

                        coverage   mean width   volatile-user coverage
  constant 6.0            98.2%       6.00              95.9%
  best constant (4.05)    89.6%       4.05              80.8%
  this model              92.1%       4.02              86.3%

The first row is the shipped behaviour: so wide that a day fell outside
it once every 78 days, which is a prompt asked once every eleven weeks.
The second is the best a single number can do, and it pays for its
average by under-covering exactly the people who move most. The third
costs no extra width and halves that unfairness.

See models/train_band_model.py for how it is fitted and
artifacts/metrics_band.json for the full figures.
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Any, Mapping, Optional, Sequence

from core import paths
from utils.band_features import BAND_FEATURE_COLUMNS, band_feature_vector

logger = logging.getLogger(__name__)

MODEL_PATH = paths.artifact("band_model.pkl")
INFO_PATH = paths.artifact("band_model_info.json")
COLUMNS_PATH = paths.artifact("feature_columns_band.json")

# Floors used only if the artifact fails to declare its own. They match
# models/train_band_model.py's defaults; the stored values win, because
# the clamp has to be the one the coverage was measured under.
FALLBACK_MIN_HALF_WIDTH = 1.5
FALLBACK_MAX_HALF_WIDTH = 15.0

_lock = threading.Lock()
_loaded = False
_model: Any = None
_min_half_width = FALLBACK_MIN_HALF_WIDTH
_max_half_width = FALLBACK_MAX_HALF_WIDTH


def _load() -> None:
    """Load once, and never raise.

    Guarded by a lock because FastAPI serves requests on a thread pool
    and two simultaneous first requests would otherwise both unpickle
    the model - wasteful, and joblib.load is not something to run twice
    concurrently on the same file.
    """
    global _loaded, _model, _min_half_width, _max_half_width
    with _lock:
        if _loaded:
            return
        _loaded = True  # set first: a failed load must not be retried per request
        try:
            if not MODEL_PATH.exists():
                logger.info("No band model artifact - the weekly band stays on its constant.")
                return

            # Checked BEFORE the model is accepted. The columns file is
            # the contract between utils/band_features.py and whatever
            # was fitted; if someone adds a feature and forgets to
            # retrain, the vector silently means something different at
            # every position past the insertion point. That is the kind
            # of skew that produces plausible-looking wrong numbers, so
            # it is refused rather than tolerated.
            if COLUMNS_PATH.exists():
                stored = json.loads(COLUMNS_PATH.read_text(encoding="utf-8")).get("features")
                if stored != BAND_FEATURE_COLUMNS:
                    logger.warning(
                        "Band model feature columns do not match utils/band_features.py "
                        "(%d stored vs %d current) - refusing to use it. Retrain with "
                        "python3 -m models.train_band_model.",
                        len(stored or []), len(BAND_FEATURE_COLUMNS),
                    )
                    return

            if INFO_PATH.exists():
                info = json.loads(INFO_PATH.read_text(encoding="utf-8"))
                _min_half_width = float(info.get("min_half_width", FALLBACK_MIN_HALF_WIDTH))
                _max_half_width = float(info.get("max_half_width", FALLBACK_MAX_HALF_WIDTH))

            import joblib

            _model = joblib.load(MODEL_PATH)
            logger.info("Band model loaded from %s", MODEL_PATH)
        except Exception:
            _model = None
            logger.exception("Band model failed to load - falling back to the constant.")


def available() -> bool:
    """Whether a personal half-width can be produced at all.

    Public so the API can tell a reader which of the two it is looking
    at rather than presenting a constant as if it were personal.
    """
    _load()
    return _model is not None


def half_width(
    scores: Sequence[float],
    days: Optional[Sequence[Mapping[str, Any]]] = None,
    prior_scores: Optional[Sequence[float]] = None,
) -> Optional[float]:
    """This user's half-width for the band, or None to use the constant.

    `scores`       the week's scores so far, OLDEST FIRST - the same
                   list api/routers/plan._week_scores returns.
    `days`         optionally the stored history entries behind those
                   scores, same order, for the habit features. Absent
                   is fine and is the documented degraded case, not an
                   error.
    `prior_scores` optionally this user's days from BEFORE this week,
                   oldest first. This is the block that tells a
                   genuinely volatile person apart from a calm one:
                   measured, coverage for the most volatile third of
                   respondents sat at 0.84 against a 0.90 promise at
                   EVERY prefix length, because three days into a week
                   the two look identical. Absent, the model behaves
                   exactly as it did before - which is also the honest
                   state for somebody in their first week.

    None means "no opinion": no artifact, no usable score, or anything
    at all went wrong. The caller keeps its constant.
    """
    _load()
    if _model is None:
        return None

    usable = [
        float(s) for s in (scores or ())
        if isinstance(s, (int, float)) and not isinstance(s, bool)
    ]
    if not usable:
        # No centre either, so there is no band to widen. The caller
        # already returns (None, None) here.
        return None

    try:
        vector = band_feature_vector(usable, days, prior_scores)
        predicted = float(_model.predict([vector])[0])
    except Exception:
        logger.exception("Band half-width prediction failed - falling back to the constant.")
        return None

    if predicted != predicted:  # NaN
        return None
    return round(min(_max_half_width, max(_min_half_width, predicted)), 2)


def reset_cache() -> None:
    """Drop the loaded model. For tests that write a fresh artifact."""
    global _loaded, _model, _min_half_width, _max_half_width
    with _lock:
        _loaded = False
        _model = None
        _min_half_width = FALLBACK_MIN_HALF_WIDTH
        _max_half_width = FALLBACK_MAX_HALF_WIDTH
