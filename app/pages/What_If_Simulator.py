"""
What-if Simulator Page

Lets the user explore "what if I changed X" scenarios on top of their
most recent real submission. Uses the real, unmodified PredictionService
for every simulated call - it just never persists the result as the
user's real prediction or writes it to their weekly history.
"""
import streamlit as st
import bootstrap

st.set_page_config(
    page_title="What-if Simulator",
    page_icon="🧪",
    layout="wide"
)

from components.theme import Theme
Theme.load()

from services.validation_service import ValidationService
from services.prediction_service import PredictionService
from services.advanced_whatif_service import AdvancedWhatIfService
from services.parallel_twin_service import ParallelTwinService
from services.future_path_service import FuturePathService
from services.dashboard_service import DashboardService
from config.analytics_settings import BEHAVIORAL_FIELD_LABELS
from components.status_badge import StatusBadge
from components.metric_card import MetricCard
from components.what_if_simulator import WhatIfSimulator
from utils.session import get_last_prediction_result, get_last_user_data

import plotly.express as px
import pandas as pd

st.title("🧪 What-if Simulator")
st.write(
    "Adjust your habits below and see how your predicted Health Score and "
    "Health Class would change - without affecting your real stored "
    "prediction or your weekly history."
)
st.divider()

base_user_data = get_last_user_data()
real_result = get_last_prediction_result()

if base_user_data is None or real_result is None:
    st.info(
        "No prediction found yet for this session. Run a real prediction "
        "first so the simulator has a starting point to tweak."
    )
    if st.button("🧠 Go to Prediction", type="primary"):
        st.switch_page("pages/Prediction.py")
    st.stop()


@st.cache_resource(show_spinner="Loading models...")
def _load_services():
    return (ValidationService(), PredictionService())


try:
    _, predictor = _load_services()
except Exception as e:
    st.error(
        "Could not load the trained model artifacts. Make sure the "
        "classification/regression models have been trained and saved "
        f"under `artifacts/` before running the app.\n\n"
        f"Details: {e}"
    )
    st.stop()

st.subheader("📌 Your Real Prediction (starting point)")
col1, col2 = st.columns(2)
with col1:
    StatusBadge.render(real_result.prediction)
with col2:
    real_score = real_result.regression_score
    MetricCard.render(
        title="Real Health Score",
        value=f"{real_score:.1f} / 100" if real_score is not None else "N/A",
    )

st.divider()

WhatIfSimulator.render(
    base_user_data=base_user_data,
    predictor=predictor,
    real_result=real_result,
)

st.divider()

# ------------------------------------------------------------
# Advanced What-if Simulator (12): Sensitivity Analysis,
# Multi-Scenario Comparison, and Goal-Seek - all real repeated calls
# to the unmodified `predictor.predict()`, never a fitted
# approximation of the model. Parallel Twin (45) is its own tab,
# auto-derived from this session's real SHAP "areas to improve".
# ------------------------------------------------------------
st.header("🧬 Advanced Simulation")

_adv_tab_sensitivity, _adv_tab_multiscenario, _adv_tab_goalseek, _adv_tab_twin, _adv_tab_futurepaths = st.tabs(
    ["📊 Sensitivity Analysis", "🔀 Multi-Scenario Comparison", "🥅 Goal Seek", "👯 Parallel Twin", "🛤️ Future Paths"]
)

_SWEEPABLE_FIELDS = [f for f, _l, _lo, _hi, _s in WhatIfSimulator.SLIDERS]

with _adv_tab_sensitivity:
    st.caption(
        "See how your predicted score responds as ONE habit changes across "
        "its full real range, holding everything else fixed - each point is "
        "a real prediction, not an estimate."
    )
    _sweep_field = st.selectbox(
        "Field to sweep",
        options=_SWEEPABLE_FIELDS,
        format_func=lambda f: BEHAVIORAL_FIELD_LABELS.get(f, f.replace("_", " ").title()),
        key="sensitivity_field",
    )
    if st.button("▶️ Run Sensitivity Analysis", key="run_sensitivity"):
        with st.spinner("Running real predictions across the range..."):
            _sweep_points = AdvancedWhatIfService.sweep_field(base_user_data, predictor, _sweep_field)
        if not _sweep_points:
            st.warning("Could not run a sweep for this field.")
        else:
            _sweep_df = pd.DataFrame([{"value": p.value, "score": p.score} for p in _sweep_points])
            fig_sweep = px.line(
                _sweep_df, x="value", y="score", markers=True,
                labels={
                    "value": BEHAVIORAL_FIELD_LABELS.get(_sweep_field, _sweep_field),
                    "score": "Predicted Wellness Score",
                },
                title=f"Sensitivity: Predicted Score vs. {BEHAVIORAL_FIELD_LABELS.get(_sweep_field, _sweep_field)}",
            )
            st.plotly_chart(fig_sweep, use_container_width=True)

with _adv_tab_multiscenario:
    st.caption(
        "Define up to 3 scenarios and compare their real predicted outcomes "
        "side by side."
    )
    _num_scenarios = st.slider("Number of scenarios", min_value=2, max_value=3, value=2, key="num_scenarios")
    _scenario_rows = []
    for _i in range(_num_scenarios):
        with st.expander(f"Scenario {_i + 1}", expanded=(_i == 0)):
            _overrides = {}
            for _field, _label, _lo, _hi, _step in WhatIfSimulator.SLIDERS:
                _default = base_user_data.get(_field, _lo)
                try:
                    _default = float(_default)
                except (TypeError, ValueError):
                    _default = _lo
                _default = min(max(_default, _lo), _hi)
                _overrides[_field] = st.slider(
                    _label, min_value=_lo, max_value=_hi, value=_default, step=_step,
                    key=f"scenario_{_i}_{_field}",
                )
        _scenario_input = AdvancedWhatIfService.build_scenario_input(base_user_data, _overrides)
        _scenario_rows.append((f"Scenario {_i + 1}", _scenario_input))

    if st.button("▶️ Compare Scenarios", key="run_multiscenario"):
        with st.spinner("Running real predictions for each scenario..."):
            _comparison_rows = []
            for _name, _scenario_input in _scenario_rows:
                try:
                    # Comparison-only: only .prediction/.regression_score/
                    # .confidence are read below, never .shap_features.
                    _res = predictor.predict(_scenario_input, compute_shap=False)
                    _comparison_rows.append({
                        "Scenario": _name,
                        "Predicted Class": _res.prediction,
                        "Predicted Score": _res.regression_score,
                        "Confidence": f"{_res.confidence:.1%}" if _res.confidence is not None else "N/A",
                    })
                except Exception as _e:
                    _comparison_rows.append({
                        "Scenario": _name, "Predicted Class": "Error",
                        "Predicted Score": None, "Confidence": str(_e),
                    })
        st.dataframe(pd.DataFrame(_comparison_rows), use_container_width=True, hide_index=True)

with _adv_tab_goalseek:
    st.caption(
        "Pick a target wellness score and a field to adjust - Goal Seek "
        "searches that field's real range for the value whose real "
        "predicted score lands closest."
    )
    _goal_field = st.selectbox(
        "Field to adjust",
        options=_SWEEPABLE_FIELDS,
        format_func=lambda f: BEHAVIORAL_FIELD_LABELS.get(f, f.replace("_", " ").title()),
        key="goal_seek_field",
    )
    _target_score = st.slider("Target wellness score", min_value=0.0, max_value=100.0, value=80.0, key="goal_seek_target")
    if st.button("🥅 Find Closest Match", key="run_goal_seek"):
        with st.spinner("Searching the real range..."):
            _goal_result = AdvancedWhatIfService.goal_seek(base_user_data, predictor, _goal_field, _target_score)
        if _goal_result is None:
            st.warning("Could not find a match for this field.")
        else:
            _gcol1, _gcol2 = st.columns(2)
            with _gcol1:
                MetricCard.render(
                    title=f"Suggested {BEHAVIORAL_FIELD_LABELS.get(_goal_field, _goal_field)}",
                    value=f"{_goal_result.best_value}",
                )
            with _gcol2:
                MetricCard.render(
                    title="Resulting Predicted Score",
                    value=f"{_goal_result.best_score:.1f}" if _goal_result.best_score is not None else "N/A",
                    help_text=f"Off target by {_goal_result.distance} points (grid resolution limited).",
                )

with _adv_tab_twin:
    st.caption(
        "Your Parallel Twin auto-adopts the top real factors this session's "
        "SHAP explanation flagged as pulling your score down - a snapshot "
        "comparison with the same real model, not a multi-day forecast."
    )
    _areas_to_improve = []
    if getattr(real_result, "shap_features", None):
        _areas_to_improve = DashboardService.split_shap_by_direction(real_result.shap_features).areas_to_improve

    if not _areas_to_improve:
        st.info("No adverse SHAP factors in this session's real prediction to build a twin from.")
    else:
        _twin_comparison = ParallelTwinService.compare(
            base_user_data=base_user_data,
            areas_to_improve=_areas_to_improve,
            real_result=real_result,
            predictor=predictor,
        )
        if _twin_comparison is None:
            st.info("None of the top factors this session are ones the twin can automatically adjust.")
        else:
            st.markdown("**Adjustments the twin made:**")
            for _adj in _twin_comparison.adjustments:
                st.write(f"- **{_adj.label}**: {_adj.old_value} → {_adj.new_value}")

            _tcol1, _tcol2, _tcol3 = st.columns(3)
            with _tcol1:
                StatusBadge.render(_twin_comparison.twin_result.prediction)
            with _tcol2:
                _twin_score = _twin_comparison.twin_result.regression_score
                MetricCard.render(
                    title="Twin's Predicted Score",
                    value=f"{_twin_score:.1f} / 100" if _twin_score is not None else "N/A",
                    delta=f"{_twin_comparison.score_delta:+.1f} vs. you" if _twin_comparison.score_delta is not None else None,
                )
            with _tcol3:
                MetricCard.render(
                    title="Health Class Changed?",
                    value="Yes" if _twin_comparison.class_changed else "No",
                )

with _adv_tab_futurepaths:
    st.caption(
        "Group C Feature 39 - a fixed set of named, plausible futures "
        "(from doing nothing to an aggressive reset), each evaluated with "
        "a real prediction - not a slider you drag, a set you compare."
    )

    _future_comparison = FuturePathService.compare(base_user_data, predictor)

    _path_cols = st.columns(len(_future_comparison.paths))
    for _col, _path in zip(_path_cols, _future_comparison.paths):
        with _col:
            st.markdown(f"**{_path.name}**")
            st.caption(_path.description)
            if _path.error:
                st.error("Could not evaluate this path.")
                continue

            StatusBadge.render(_path.prediction)

            _delta = _path.score_delta_vs_status_quo
            _delta_str = None
            if _delta is not None and _path.key != "status_quo":
                _is_meaningful = _future_comparison.is_delta_meaningful(_path)
                _delta_str = f"{_delta:+.1f}" if _is_meaningful else f"{_delta:+.1f} (within model noise)"

            MetricCard.render(
                title="Wellness Score",
                value=f"{_path.regression_score:.1f} / 100" if _path.regression_score is not None else "N/A",
                delta=_delta_str,
            )

            if _path.adjustments:
                with st.expander(f"{len(_path.adjustments)} habit changes"):
                    for _adj in _path.adjustments:
                        st.write(f"- {_adj['label']}: {_adj['old_value']} → {_adj['new_value']}")

    if _future_comparison.best_path_key:
        _best = next(p for p in _future_comparison.paths if p.key == _future_comparison.best_path_key)
        st.success(f"Best projected outcome: **{_best.name}**")
