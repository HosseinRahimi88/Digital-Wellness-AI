"""
About Page
"""
import streamlit as st
import bootstrap

st.set_page_config(
    page_title="About",
    page_icon="ℹ️",
    layout="wide"
)

from components.theme import Theme
Theme.load()

st.title("ℹ About")

st.write("""
**Digital Wellness AI**  
Version 1.0  

This system analyzes digital habits using Machine Learning
to estimate digital wellness and provide personalized recommendations.

Developed for AI Competition.
""")