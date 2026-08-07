"""
Model Manager
-------------
Process-wide singleton responsible for loading every ML artifact
(classification model, regression model, feature columns, metrics,
model info, and the SHAP explainer) exactly once, and handing out the
same in-memory objects to every service/request that needs them.

Why this exists
----------------
Before this module existed, every `PredictionService()` instantiation
created its *own* `ModelRegistry` instances (and its own `SHAPService`,
which builds a brand-new SHAP explainer). Streamlit's `st.cache_resource`
already keeps this to "once per cached function", but each *page*
(`Prediction.py`, `What_If_Simulator.py`) declared its own
`@st.cache_resource`-wrapped loader function, and `st.cache_resource`
keys its cache by function identity - not by what the function returns.
Two visually-identical loader functions in two different modules are two
different cache entries. Net effect: the ~10MB classifier + regressor
pair, plus a freshly rebuilt SHAP explainer, were being loaded **twice**
per server process, and would be loaded again for every additional page
that needed predictions.

`ModelManager` fixes this at the source: regardless of how many
services, pages, or worker threads ask for it, `ModelManager.instance()`
returns the exact same object, and the underlying model artifacts are
read from disk exactly once per process.

Thread-safety
-------------
`instance()` uses double-checked locking so concurrent first-callers
(e.g. 10 simultaneous requests hitting a cold process) can't each start
their own load. Once loaded, all exposed attributes are read-only
references to immutable-in-practice objects (fitted sklearn Pipelines,
plain dicts/lists) - concurrent *reads* of a fitted scikit-learn
estimator's `.predict()` / `.predict_proba()` are safe as long as no one
calls `.fit()` again at runtime, which this codebase never does outside
the offline training scripts under `models/train_*.py`.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from models.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Thread-safe singleton holding every loaded model artifact.

    Use `ModelManager.instance()` everywhere instead of constructing
    `ModelRegistry`/`SHAPService` directly, so the whole process shares
    one copy of every model and explainer.
    """

    _instance: Optional["ModelManager"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        # Guard against accidental direct instantiation bypassing the
        # singleton accessor (would silently duplicate the load).
        if ModelManager._instance is not None:
            raise RuntimeError(
                "ModelManager is a singleton. Use ModelManager.instance() "
                "instead of ModelManager()."
            )

        logger.info("ModelManager: loading model artifacts (once per process)...")

        self.classification_registry = ModelRegistry(task="classification")
        self.classification_registry.validate()
        self.classification_model = self.classification_registry.model
        self.classification_feature_columns = self.classification_registry.feature_columns
        self.classes = self.classification_registry.classes

        self.regression_registry = ModelRegistry(task="regression")
        self.regression_registry.validate()
        self.regression_model = self.regression_registry.model
        self.regression_feature_columns = self.regression_registry.feature_columns

        # Import lazily so unit tests that don't need SHAP (and
        # environments where the optional `shap` dependency isn't
        # installed) don't pay the import cost / fail at module import
        # time just for touching model_manager.
        from services.shap_service import SHAPService

        # Built once - constructing a SHAP explainer (especially
        # TreeExplainer) has real, non-trivial setup cost. Reusing one
        # instance across every prediction is itself a perf win on top
        # of the single-load win.
        self.shap_service = SHAPService(self.regression_model)

        # Same rationale as SHAPService above: built once here so the
        # (validation-set-sized) split-conformal calibration pass happens
        # exactly once per process rather than once per PredictionService
        # instantiation. Imported lazily to avoid a hard import-time
        # dependency on models/data_loader.py + data/validation.csv for
        # tests/tools that only need the raw models.
        from services.uncertainty_service import UncertaintyService

        self.uncertainty_service = UncertaintyService(model_manager=self)

        # Group C Feature 02 - Persona Detection. Independent artifact
        # (models/train_persona.py), loaded once here so every page/
        # service shares one copy instead of re-reading the pickle from
        # disk per request. Missing/untrained artifact degrades to an
        # unavailable PersonaService rather than blocking startup - the
        # rest of the app must keep working even if persona training
        # hasn't been run yet.
        from services.persona_service import PersonaService

        self.persona_service = PersonaService()

        logger.info("ModelManager: all artifacts loaded and cached in memory.")

    # ======================================================
    # Singleton accessor
    # ======================================================

    @classmethod
    def instance(cls) -> "ModelManager":
        """
        Return the process-wide ModelManager, creating it on first call.

        Double-checked locking: the lock is only taken when the instance
        might not exist yet, so the hot path (already loaded) never pays
        for lock acquisition.
        """
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """
        Drop the cached singleton. Intended for tests only, so each test
        can assert load-once behavior from a clean slate without the
        interpreter-wide state leaking between test cases.
        """
        with cls._instance_lock:
            cls._instance = None
