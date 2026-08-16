"""
Dashboard Display Settings
---------------------------
Small display-tuning constants for the Dashboard page's "What's Driving
Your Score" section. Pulled out of legacy/streamlit_app/pages/Dashboard.py so the
threshold isn't a magic number buried in UI code.
"""

# How many top SHAP-ranked strengths / areas-to-improve to list per tab.
MAX_SHAP_HIGHLIGHTS = 5
