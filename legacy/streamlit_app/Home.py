"""
Home Page - Digital Wellness AI
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="Digital Wellness AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

from components.theme import Theme
Theme.load()

from utils.session import get_current_account

# ===================================================
# Main Page Content
# ===================================================

st.title("🧠 Digital Wellness AI")
st.subheader("AI-Powered Digital Health Analyzer")

_account = get_current_account()
if _account is not None:
    st.caption(f"Welcome back, {_account.display_name} 👋")
else:
    st.caption("Using this app anonymously. [Log in or create an account](./Login) to save your history to it.")

st.write("""
Analyze digital habits, detect unhealthy patterns,
predict digital wellness, and receive personalized
recommendations powered by Machine Learning.
""")

st.write("")

# ---------------------------------------------------
# Navigation Buttons
# ---------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚀 Predict Now", use_container_width=True, type="primary"):
        st.switch_page("pages/Prediction.py")

with col2:
    if st.button("📊 Analytics", use_container_width=True):
        st.switch_page("pages/Analytics.py")

with col3:
    if st.button("🤖 AI Coach", use_container_width=True):
        st.switch_page("pages/AI_Coach.py")

col_dash, col_wi, col_sim = st.columns(3)

with col_dash:
    if st.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/Dashboard.py")

with col_wi:
    if st.button("📅 Weekly Insights", use_container_width=True):
        st.switch_page("pages/Weekly_Insights.py")

with col_sim:
    if st.button("🧪 What-if Simulator", use_container_width=True):
        st.switch_page("pages/What_If_Simulator.py")

if st.button("🧭 Your Journey", use_container_width=True):
    st.switch_page("pages/Journey.py")


if _account is None:
    if st.button("🔐 Log In / Create Account", use_container_width=True):
        st.switch_page("pages/Login.py")

if st.button("🧭 Onboarding / Personalize", use_container_width=True):
    st.switch_page("pages/Onboarding.py")

if st.button("👤 Profile", use_container_width=True):
    st.switch_page("pages/Profile.py")

if st.button("👨‍👩‍👧‍👦 Family Mode", use_container_width=True):
    st.switch_page("pages/Family.py")

st.divider()

# ---------------------------------------------------
# Features Overview
# ---------------------------------------------------
st.header("✨ Features")

c1, c2 = st.columns(2)

with c1:
    st.success("🧠 AI Prediction")
    st.success("📱 Screen Time Analysis")
    st.success("😴 Sleep Analysis")

with c2:
    st.success("📈 Analytics Dashboard")
    st.success("🤖 Personalized Recommendations")
    st.success("⚡ Healthy Habit Suggestions")

st.divider()

# ---------------------------------------------------
# Workflow Section
# ---------------------------------------------------
st.header("⚙️ How It Works")

st.markdown("""
### ① Enter Your Information
↓
### ② AI Analyzes Your Digital Habits
↓
### ③ Predict Health Status
↓
### ④ Receive Personalized Recommendations
""")

st.divider()

# ---------------------------------------------------
# Project Highlights
# ---------------------------------------------------
st.header("🚀 Project Highlights")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Machine Learning", "✓")

with col2:
    st.metric("Dashboard", "✓")

with col3:
    st.metric("Visualization", "✓")

with col4:
    st.metric("Personalization", "✓")

st.divider()

st.caption("Digital Wellness AI • Version 1.0")