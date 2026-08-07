"""
Model Performance Page
"""
import streamlit as st
import pandas as pd
import bootstrap

st.set_page_config(
    page_title="Model Performance",
    page_icon="📈",
    layout="wide"
)

from components.theme import Theme
Theme.load()

from services.model_service import ModelService

st.title("🤖 Model Performance")


@st.cache_resource
def _get_model_service() -> ModelService:
    return ModelService()


@st.cache_data(show_spinner="Loading model metrics...")
def _load_classification_metrics():
    service = _get_model_service()
    return service.classification_metrics(), service.classification_info()


try:
    metrics, model_info = _load_classification_metrics()
    test_metrics = metrics.get("test", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Accuracy", f"{test_metrics.get('accuracy', 0) * 100:.1f}%")

    with col2:
        st.metric("Precision", f"{test_metrics.get('precision', 0) * 100:.1f}%")

    with col3:
        st.metric("Recall", f"{test_metrics.get('recall', 0) * 100:.1f}%")

    with col4:
        st.metric("F1 Score", f"{test_metrics.get('f1', 0) * 100:.1f}%")

    st.caption(
        f"Best model: **{metrics.get('best_model', 'Unknown')}** "
        f"(trained {model_info.get('saved_at', 'unknown date')})"
    )

    if "confusion_matrix" in test_metrics:
        st.subheader("Confusion Matrix (Test Set)")
        classes = model_info.get("classes") or list(range(len(test_metrics["confusion_matrix"])))
        st.dataframe(
            pd.DataFrame(test_metrics["confusion_matrix"], index=classes, columns=classes),
            use_container_width=True,
        )

    with st.expander("Validation results for all candidate models"):
        st.json(metrics.get("validation", {}))

except FileNotFoundError:
    st.warning(
        "No trained classification model found yet. Run the training "
        "pipeline (`python -m models.train_model --task classification`) "
        "to generate real metrics - this page will show them "
        "automatically once `artifacts/metrics.json` exists."
    )

st.divider()
st.header("📈 Regression (Wellness Score) Performance")


@st.cache_data(show_spinner="Loading regression metrics...")
def _load_regression_metrics():
    service = _get_model_service()
    return service.regression_metrics(), service.regression_info()


try:
    reg_metrics, reg_model_info = _load_regression_metrics()
    reg_test_metrics = reg_metrics.get("test", {})

    rcol1, rcol2, rcol3 = st.columns(3)

    with rcol1:
        st.metric("R²", f"{reg_test_metrics.get('R2', 0):.4f}")

    with rcol2:
        st.metric("MAE", f"{reg_test_metrics.get('MAE', 0):.2f}")

    with rcol3:
        st.metric("RMSE", f"{reg_test_metrics.get('RMSE', 0):.2f}")

    st.caption(
        f"Best model: **{reg_metrics.get('best_model', 'Unknown')}** "
        f"(trained {reg_model_info.get('saved_at', 'unknown date')})"
    )

    with st.expander("Validation results for all candidate regression models"):
        st.json(reg_metrics.get("validation", {}))

except FileNotFoundError:
    st.warning(
        "No trained regression model found yet. Run the training "
        "pipeline (`python -m models.train_model --task regression`) "
        "to generate real metrics - this page will show them "
        "automatically once `artifacts/metrics_regression.json` exists."
    )