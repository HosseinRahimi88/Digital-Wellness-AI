"""
Form Generator Utility
----------------------
Generates a clean, highly effective Streamlit UI form.
Calculates all derived, composite, and ratio features dynamically under the hood 
to supply the trained ML pipeline with precise inputs.
"""

from typing import Any, Dict
import streamlit as st

from utils.feature_derivation import derive_features


class FormGenerator:
    """Utility class to render a simplified UI form and compute derived features."""

    @classmethod
    def render(cls) -> Dict[str, Any]:
        """Renders input form widgets for core user inputs and calculates derived metrics."""
        user_inputs: Dict[str, Any] = {}

        st.subheader("📋 Enter User Information")

        # -----------------------------------------------------------------
        # 1. Demographics & Profile
        # -----------------------------------------------------------------
        col1, col2 = st.columns(2)
        with col1:
            user_inputs["age"] = st.number_input(
                "Age", min_value=10, max_value=100, value=22, step=1, key="field_age"
            )
            user_inputs["gender"] = st.selectbox(
                "Gender", options=["Male", "Female", "Non-binary", "Unknown"], index=0, key="field_gender"
            )
            user_inputs["occupation_group"] = st.selectbox(
                "Occupation", 
                options=["Student", "Employee", "Freelancer", "Self-employed", "Caregiver/Home", "Retired", "Unemployed", "Other"],
                index=6, key="field_occupation"  # Default: Student
            )
            user_inputs["region_group"] = st.selectbox(
                "Region", 
                options=["Middle East", "Europe", "North America", "Asia", "Latin America", "Africa", "Oceania"],
                index=0, key="field_region"
            )

        with col2:
            user_inputs["education_group"] = st.selectbox(
                "Education Level", 
                options=["Bachelor", "Master", "Doctoral", "High School or Below", "Some College/Vocational"],
                index=0, key="field_education"
            )
            user_inputs["device_category"] = st.selectbox(
                "Primary Device", options=["Smartphone", "Desktop", "Tablet", "Smart TV", "Wearable"], index=2, key="field_device"
            )
            user_inputs["primary_platform"] = st.selectbox(
                "Primary Platform", 
                options=["Instagram", "YouTube", "TikTok", "X (Twitter)", "Facebook", "LinkedIn", "Discord", "Reddit", "WhatsApp", "Telegram", "Snapchat", "Pinterest", "Bluesky", "Threads", "RedNote"],
                index=14, key="field_platform" # Default: YouTube
            )

        c1, c2, c3 = st.columns(3)
        with c1:
            user_inputs["purpose_group"] = st.selectbox(
                "Main Purpose of Use", 
                options=["Education", "Work/Career", "Entertainment", "Social Connection", "News/Information", "Content Creation", "Shopping"],
                index=1, key="field_purpose"
            )
        with c2:
            user_inputs["is_content_creator"] = st.checkbox("Is a Content Creator?", value=False, key="field_creator")
        with c3:
            user_inputs["uses_screen_time_limits"] = st.checkbox("Uses Screen-Time Limits?", value=True, key="field_limits")

        st.divider()

        # -----------------------------------------------------------------
        # 2. Time & Calendar
        # -----------------------------------------------------------------
        user_inputs["day_index"] = 1
        user_inputs["day_of_week"] = st.selectbox(
            "Day of the Week", 
            options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            index=1, key="field_dow"
        )
        # Automatically determine weekend status
        user_inputs["is_weekend"] = 1 if user_inputs["day_of_week"] in ["Saturday", "Sunday"] else 0

        st.divider()

        # -----------------------------------------------------------------
        # 3. Screen Time Breakdown (Minutes per day)
        # -----------------------------------------------------------------
        st.markdown("### ⏱️ Screen Time Activity (Minutes/Day)")
        
        c1, c2 = st.columns(2)
        with c1:
            user_inputs["social_min"] = st.number_input("Social Media Time (min)", min_value=0.0, max_value=1440.0, value=45.0, step=5.0, key="field_social")
            user_inputs["gaming_min"] = st.number_input("Gaming Time (min)", min_value=0.0, max_value=1440.0, value=0.0, step=5.0, key="field_gaming")
            user_inputs["work_study_min"] = st.number_input("Work/Study Screen Time (min)", min_value=0.0, max_value=1440.0, value=120.0, step=5.0, key="field_work")
        
        with c2:
            user_inputs["video_min"] = st.number_input("Video/Entertainment Time (min)", min_value=0.0, max_value=1440.0, value=30.0, step=5.0, key="field_video")
            user_inputs["other_min"] = st.number_input("Other Screen Time (min)", min_value=0.0, max_value=1440.0, value=15.0, step=5.0, key="field_other")
            user_inputs["night_screen_min"] = st.number_input("Late-Night Screen Use (min)", min_value=0.0, max_value=600.0, value=0.0, step=5.0, key="field_night")

        c1, c2 = st.columns(2)
        with c1:
            user_inputs["pre_sleep_screen_min"] = st.number_input("Screen Use Right Before Sleep (min)", min_value=0.0, max_value=300.0, value=10.0, step=5.0, key="field_presleep")
        with c2:
            # Feature Selection removed this as a standalone model input for
            # both tasks (statistically insignificant permutation importance),
            # but it is still collected here because it feeds
            # digital_dependence_0_100 below, which IS a retained feature.
            user_inputs["first_check_after_waking_min"] = st.number_input("Minutes Until First Phone Check After Waking", min_value=0.0, max_value=300.0, value=45.0, step=5.0, key="field_waking")

        # Auto-calculate total screen time
        total_calc = (user_inputs["social_min"] + 
                      user_inputs["gaming_min"] + 
                      user_inputs["work_study_min"] + 
                      user_inputs["video_min"] + 
                      user_inputs["other_min"])
        user_inputs["total_screen_min"] = max(total_calc, 1.0) # avoid division by zero

        st.info(f"💡 **Calculated Total Screen Time:** {user_inputs['total_screen_min']:.0f} minutes ({user_inputs['total_screen_min']/60:.1f} hours/day)")

        st.divider()

        # -----------------------------------------------------------------
        # 4. Device Interaction
        # -----------------------------------------------------------------
        st.markdown("### 🔔 Device Interaction")
        c1, c2 = st.columns(2)
        with c1:
            user_inputs["notifications_per_day"] = st.number_input("Notifications / Day", min_value=0, max_value=2000, value=30, key="field_notifs")
            user_inputs["pickups_per_day"] = st.number_input("Phone Pickups / Day", min_value=0, max_value=500, value=20, key="field_pickups")
        with c2:
            user_inputs["app_opens_per_day"] = st.number_input("App Opens / Day", min_value=0, max_value=1000, value=25, key="field_appopens")
            # Feature Selection removed this as a standalone model input for
            # both tasks (statistically insignificant permutation importance),
            # but it is still collected here because it feeds
            # fragmentation_index_0_100 below, which IS a retained feature.
            user_inputs["sessions_per_day"] = st.number_input("Usage Sessions / Day", min_value=0, max_value=200, value=12, key="field_sessions")

        st.divider()

        # -----------------------------------------------------------------
        # 5. Wellbeing, Sleep & Lifestyle
        # -----------------------------------------------------------------
        st.markdown("### 😴 Sleep & Health")
        c1, c2 = st.columns(2)
        with c1:
            user_inputs["sleep_hours"] = st.slider("Sleep Duration (Hours)", 0.0, 15.0, 8.0, 0.5, key="field_sleephours")
            user_inputs["stress_0_10"] = st.slider("Stress Level (0-10)", 0.0, 10.0, 2.0, 0.5, key="field_stress")
            user_inputs["mental_fatigue_0_10"] = st.slider("Mental Fatigue (0-10)", 0.0, 10.0, 2.0, 0.5, key="field_fatigue")
            user_inputs["anxiety_0_27"] = st.number_input("Anxiety Score (0-27)", min_value=0.0, max_value=27.0, value=2.0, key="field_anxiety")
            user_inputs["low_mood_0_27"] = st.number_input("Low Mood Score (0-27)", min_value=0.0, max_value=27.0, value=1.0, key="field_lowmood")
            user_inputs["fomo_1_10"] = st.slider("Fear of Missing Out - FOMO (1-10)", 1.0, 10.0, 2.0, 0.5, key="field_fomo")

        with c2:
            user_inputs["sleep_quality_1_10"] = st.slider("Sleep Quality (1-10)", 1.0, 10.0, 8.5, 0.5, key="field_sleepqual")
            user_inputs["happiness_0_10"] = st.slider("Happiness (0-10)", 0.0, 10.0, 8.5, 0.5, key="field_happiness")
            user_inputs["loneliness_1_10"] = st.slider("Loneliness (1-10)", 1.0, 10.0, 2.0, 0.5, key="field_loneliness")
            user_inputs["self_esteem_1_10"] = st.slider("Self-Esteem (1-10)", 1.0, 10.0, 8.0, 0.5, key="field_esteem")
            user_inputs["social_comparison_1_10"] = st.slider("Social Comparison Tendency (1-10)", 1.0, 10.0, 2.0, 0.5, key="field_socialcomp")
            user_inputs["life_satisfaction_1_10"] = st.slider("Life Satisfaction (1-10)", 1.0, 10.0, 8.5, 0.5, key="field_lifesat")

        st.divider()

        st.markdown("### ⚡ Focus & Productivity")
        c1, c2, c3 = st.columns(3)
        with c1:
            user_inputs["focus_0_100"] = st.slider("Focus Score (0-100)", 0.0, 100.0, 85.0, 1.0, key="field_focus")
        with c2:
            user_inputs["productivity_0_100"] = st.slider("Productivity Score (0-100)", 0.0, 100.0, 85.0, 1.0, key="field_prod")
        with c3:
            user_inputs["physical_activity_min_per_day"] = st.number_input("Physical Activity (min/day)", min_value=0.0, max_value=300.0, value=60.0, key="field_phys")

        user_inputs["caffeine_cups_per_day"] = st.number_input("Caffeine Intake (cups/day)", min_value=0.0, max_value=20.0, value=1.0, key="field_caff")

        # -----------------------------------------------------------------
        # 6. Smart Dynamic Feature Computation (Under the Hood)
        # -----------------------------------------------------------------
        # Extracted into utils/feature_derivation.derive_features so the
        # What-if Simulator can recompute the exact same derived/ratio/
        # density features when the user tweaks a value - see that module
        # for the (unchanged) formulas. Behavior here is identical to
        # before this refactor.
        user_inputs = derive_features(user_inputs)

        return user_inputs