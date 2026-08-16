"""
Improvement Plan Card Component
----------------------------------
Renders the rule-based 7-day plan produced by
services.improvement_plan_service.ImprovementPlanService. Presentation
only - all scheduling logic lives in the service.

`render()` (used by app/pages/AI_Coach.py, unchanged) keeps its
original session-only checkbox behavior. `render_persistent()` (used
by app/pages/Weekly_Insights.py) is the same layout backed by
services.plan_progress_service.PlanProgressService instead, so
checkmarks survive across page loads/sessions for a given user and
week - see that service's docstring for why.
"""

from __future__ import annotations

import streamlit as st

from services.improvement_plan_service import ImprovementPlan
from services.plan_progress_service import PlanProgressService


class ImprovementPlanCard:

    @staticmethod
    def render(plan: ImprovementPlan, title: str = "🗓️ Your 7-Day Improvement Plan") -> None:
        if title:
            st.subheader(title)

        st.markdown(plan.intro)
        st.write("")

        tabs = st.tabs([f"{d.icon} {d.day_label}" for d in plan.days])

        completed = 0
        for tab, day in zip(tabs, plan.days):
            with tab:
                st.markdown(f"#### {day.icon} {day.theme}")
                day_done = 0
                for i, task in enumerate(day.tasks):
                    key = f"plan_day{day.day_number}_task{i}"
                    checked = st.checkbox(task, key=key)
                    if checked:
                        day_done += 1
                if day.tip:
                    st.caption(f"💡 {day.tip}")
                if day_done == len(day.tasks) and day.tasks:
                    st.success("Nice - all of today's tasks are checked off!")
                completed += day_done

        total_tasks = sum(len(d.tasks) for d in plan.days)
        if total_tasks:
            st.write("")
            progress = completed / total_tasks
            st.progress(progress, text=f"Plan progress: {completed}/{total_tasks} tasks checked off")

        st.caption(
            "This plan is generated from simple, transparent rules based on your "
            "predicted health class, wellness score, and habit inputs - no AI "
            "writing, no retraining. Checkmarks are for this browser session only."
        )

    @staticmethod
    def render_persistent(
        plan: ImprovementPlan,
        progress_service: PlanProgressService,
        title: str = "🗓️ Your Weekly Plan",
    ) -> None:
        """Same layout as render(), but checkbox state is loaded from
        and written back to `progress_service` (persists across
        sessions), instead of only living in `st.session_state` for
        this browser session."""
        if title:
            st.subheader(title)

        with st.expander("Why this plan was created"):
            st.write(plan.intro)
            if plan.focus_areas:
                st.write("Focus areas: " + ", ".join(plan.focus_areas))

        st.write("")

        already_completed = progress_service.get_completed()

        tabs = st.tabs([f"{d.icon} {d.day_label}" for d in plan.days])

        completed = 0
        for tab, day in zip(tabs, plan.days):
            with tab:
                st.markdown(f"#### {day.icon} {day.theme}")
                day_done = 0
                for i, task in enumerate(day.tasks):
                    key = f"weekly_plan_day{day.day_number}_task{i}"
                    was_checked = (day.day_number, i) in already_completed
                    checked = st.checkbox(task, value=was_checked, key=key)
                    if checked != was_checked:
                        progress_service.set_completed(day.day_number, i, checked)
                    if checked:
                        day_done += 1
                if day.tip:
                    st.caption(f"💡 {day.tip}")
                if day_done == len(day.tasks) and day.tasks:
                    st.success("Nice - all of today's tasks are checked off!")
                completed += day_done

        total_tasks = sum(len(d.tasks) for d in plan.days)
        if total_tasks:
            st.write("")
            progress = completed / total_tasks
            st.progress(progress, text=f"This week's progress: {completed}/{total_tasks} tasks checked off")

        st.caption(
            "This plan is generated from simple, transparent rules based on your "
            "predicted health class, wellness score, and habit inputs - no AI "
            "writing, no retraining. Checkmarks are saved to your account and "
            "reset each new week."
        )
