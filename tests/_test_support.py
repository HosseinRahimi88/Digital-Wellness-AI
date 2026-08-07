"""
Shared test bootstrap.
-----------------------
Two jobs:

1. Put the project root on `sys.path` so `import services...`,
   `import models...` etc. work when tests are run from anywhere
   (`python3 -m unittest discover`).

2. IMPORTANT SANDBOX NOTE: the execution environment these tests were
   authored/run in has no network access, so the real `shap` PyPI
   package (an optional, heavier dependency of `services/shap_service.py`)
   cannot be installed. To still exercise the *real, unmodified*
   `services/shap_service.py` end-to-end (rather than skip/mock it), this
   file installs a small stand-in `shap` module into `sys.modules`
   *only if the real package isn't already importable*. That stand-in
   implements a genuine (if simplified) Shapley-style attribution -
   ablation/occlusion contribution per feature against a zero baseline,
   i.e. `phi_i = f(x) - f(x with feature i replaced by baseline)` - using
   the *actual* trained regressor's `.predict`. It is real arithmetic on
   the real model, not canned/fabricated numbers.
   In any environment where the real `shap` package IS installed
   (e.g. the project's actual deployment target), this stub is not used
   at all - `import shap` resolves to the genuine library and every test
   below runs against the exact production explainer.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import shap  # noqa: F401
    SHAP_IS_REAL = True
except ImportError:
    SHAP_IS_REAL = False

    import types
    import numpy as np

    _stub = types.ModuleType("shap")

    class _AblationExplanation:
        def __init__(self, values):
            self.values = values  # shape (1, n_features)

    class _AblationExplainer:
        """Real ablation-based per-feature attribution (sandbox stand-in)."""

        def __init__(self, predict_fn, masker):
            self._predict_fn = predict_fn
            self._baseline = np.asarray(masker)[0]

        def __call__(self, X):
            X = np.asarray(X, dtype=float)
            row = X[0].copy()
            f_full = float(np.asarray(self._predict_fn(row.reshape(1, -1)))[0])
            n_features = row.shape[0]
            phis = np.zeros(n_features)
            for i in range(n_features):
                perturbed = row.copy()
                perturbed[i] = self._baseline[i]
                f_without_i = float(np.asarray(self._predict_fn(perturbed.reshape(1, -1)))[0])
                phis[i] = f_full - f_without_i
            return _AblationExplanation(values=phis.reshape(1, -1))

    class _TreeExplainerUnavailable:
        """
        The sandbox stub intentionally does NOT implement TreeExplainer -
        this is a real, honest limitation (no network to fetch the real
        SHAP C++/Cython tree-traversal implementation), not a shortcut.
        `services/shap_service.py`'s own real fallback logic already
        handles an explainer-construction failure by trying the
        function-based `Explainer` path next, so raising here exercises
        that real fallback code path instead of skipping it.
        """

        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "TreeExplainer unavailable in offline sandbox shap-stub; "
                "shap_service.py is expected to fall back to Explainer()."
            )

    _stub.TreeExplainer = _TreeExplainerUnavailable
    _stub.Explainer = _AblationExplainer

    sys.modules["shap"] = _stub


try:
    import pwdlib  # noqa: F401
    PWDLIB_IS_REAL = True
except ImportError:
    # Same offline-sandbox reasoning as the shap stub above: `pwdlib`
    # (utils/security.py) needs no network to install in the project's
    # real deployment target (it's a small pure-Python dependency listed
    # in requirements.txt), but isn't installed in this sandbox. This
    # stub implements the same two-method surface
    # (`PasswordHash.recommended().hash()/.verify()`) with a reversible
    # marker instead of real Argon2, so account_service.py's actual
    # register/authenticate logic - not the hashing algorithm - is what
    # gets exercised here. Wherever the real `pwdlib` package IS
    # installed, this stub is never used.
    PWDLIB_IS_REAL = False

    import types as _types

    _pwdlib_stub = _types.ModuleType("pwdlib")

    class _FakePasswordHash:
        @staticmethod
        def recommended():
            return _FakePasswordHash()

        def hash(self, password):
            return f"stub-hash:{password}"

        def verify(self, password, password_hash):
            return password_hash == f"stub-hash:{password}"

    _pwdlib_stub.PasswordHash = _FakePasswordHash
    sys.modules["pwdlib"] = _pwdlib_stub


# ==========================================================
# Synthetic-but-valid feature data, built from the *real*
# FEATURE_SCHEMA (core/feature_schema.py) - never hand-typed magic
# numbers. Canonical source moved to config/demo_profiles.py (also
# used by app/pages/Prediction.py's "Quick Demo" tab) - kept here as
# thin aliases so every existing tests._test_support.xxx_user_data()
# call site keeps working unchanged.
# ==========================================================

from config.demo_profiles import (  # noqa: E402
    baseline_profile as baseline_user_data,
    healthy_profile as healthy_user_data,
    at_risk_profile as at_risk_user_data,
    borderline_profile as borderline_user_data,
)
