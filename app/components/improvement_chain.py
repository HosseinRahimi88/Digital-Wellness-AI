"""
Improvement Chain Component
-------------------------------
A compact "chain" visualization of the current week's 7-day
improvement plan - one link per day, linked together, filled in once
all of that day's tasks are checked off. This is a visual summary that
sits alongside app/components/improvement_plan_card.py's existing
tabbed detail view (which keeps the day-by-day task checkboxes); this
component doesn't duplicate that task logic; it just reads the same
already-persisted completion state from
services/plan_progress_service.py to draw the chain.
"""

from __future__ import annotations

import streamlit as st

from services.improvement_plan_service import ImprovementPlan
from services.plan_progress_service import PlanProgressService


class ImprovementChain:

    @staticmethod
    def render(
        plan: ImprovementPlan,
        progress_service: PlanProgressService,
        title: str = "🔗 This Week's Improvement Chain",
    ) -> None:
        if title:
            st.caption(title)

        completed_pairs = progress_service.get_completed()

        links_html = []
        fully_done_count = 0
        for day in plan.days:
            total_tasks = len(day.tasks)
            done_tasks = sum(
                1 for i in range(total_tasks) if (day.day_number, i) in completed_pairs
            )
            is_full = total_tasks > 0 and done_tasks == total_tasks
            is_partial = 0 < done_tasks < total_tasks
            fully_done_count += 1 if is_full else 0

            if is_full:
                bg, border, icon = "#39d353", "#2ea043", "✓"
            elif is_partial:
                bg, border, icon = "#f1c40f", "#d4ac0d", "•"
            else:
                bg, border, icon = "#ebedf0", "#d0d0d0", ""

            links_html.append(
                f'<div title="{day.day_label}: {done_tasks}/{total_tasks} tasks done" style="'
                f'width:38px; height:38px; border-radius:50%; background:{bg}; '
                f'border:2px solid {border}; display:flex; align-items:center; '
                f'justify-content:center; font-weight:700; font-size:14px; flex-shrink:0;">'
                f'{icon}</div>'
            )

        link_line = (
            '<div style="height:3px; width:16px; background:#d0d0d0; flex-shrink:0;"></div>'
        )
        chain_html = link_line.join(links_html)

        day_labels_html = "".join(
            f'<div style="width:38px; text-align:center; font-size:10px; opacity:0.7; margin-right:19px;">{d.day_label.split()[-1] if " " in d.day_label else d.day_label}</div>'
            for d in plan.days
        )

        st.markdown(
            f'<div style="display:flex; align-items:center; gap:0; overflow-x:auto; padding:6px 0;">{chain_html}</div>'
            f'<div style="display:flex; overflow-x:auto;">{day_labels_html}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"{fully_done_count}/{len(plan.days)} days fully completed this week.")
