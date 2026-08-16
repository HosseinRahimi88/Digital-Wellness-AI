"""
Weekly Story Card Component
-----------------------------
Generates a plain-language weekly summary from real HistoryService
entries (real regression scores + raw habit fields the user actually
submitted through PredictionService). No mock/generated text data -
every sentence is built from an actual numeric delta.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from services.identity.history_service import HistoryService, WeekSummary


class StoryCard:

    @staticmethod
    def _pct_change(old: Optional[float], new: Optional[float]) -> Optional[float]:
        if old is None or new is None or old == 0:
            return None
        return round(((new - old) / abs(old)) * 100, 1)

    @staticmethod
    def _trend_sentence(
        label: str,
        old: Optional[float],
        new: Optional[float],
        unit: str,
        higher_is_better: bool,
    ) -> Optional[str]:
        if old is None or new is None:
            return None
        delta = round(new - old, 1)
        if abs(delta) < 0.05:
            return f"Your {label} stayed steady around {new}{unit}."

        improved = (delta > 0) == higher_is_better
        verb = "improved" if improved else "declined"
        direction = "up" if delta > 0 else "down"
        return (
            f"Your {label} {verb} - {direction} {abs(delta)}{unit}, "
            f"from {old}{unit} to {new}{unit}."
        )

    @classmethod
    def _build_lines(
        cls,
        current: WeekSummary,
        previous: Optional[WeekSummary],
        comparison_label: str,
    ) -> list[str]:
        lines: list[str] = []

        if current.avg_health_score is not None:
            if previous and previous.avg_health_score is not None:
                sentence = cls._trend_sentence(
                    "digital wellness score", previous.avg_health_score,
                    current.avg_health_score, " pts", higher_is_better=True,
                )
                if sentence:
                    lines.append(sentence)
            else:
                lines.append(
                    f"This week your average digital wellness score was "
                    f"{current.avg_health_score:.1f}/100."
                )

        if previous:
            s = cls._trend_sentence(
                "screen time", previous.avg_total_screen_min,
                current.avg_total_screen_min, " min/day", higher_is_better=False,
            )
            if s:
                lines.append(s)

            s = cls._trend_sentence(
                "social media time", previous.avg_social_min,
                current.avg_social_min, " min/day", higher_is_better=False,
            )
            if s:
                lines.append(s)

            s = cls._trend_sentence(
                "sleep", previous.avg_sleep_hours,
                current.avg_sleep_hours, " hrs", higher_is_better=True,
            )
            if s:
                lines.append(s)

            s = cls._trend_sentence(
                "focus", previous.avg_focus_0_100,
                current.avg_focus_0_100, " pts", higher_is_better=True,
            )
            if s:
                lines.append(s)

            s = cls._trend_sentence(
                "stress level", previous.avg_stress_0_10,
                current.avg_stress_0_10, " pts", higher_is_better=False,
            )
            if s:
                lines.append(s)

        if not lines:
            lines.append(
                "Not enough logged days yet to describe a trend - keep "
                "running predictions and check back soon."
            )

        return lines

    @classmethod
    def render(
        cls,
        history_service: HistoryService,
        title: str = "🗞️ Your Weekly Story",
    ) -> None:
        current_entries = history_service.current_week_entries()
        previous_entries = history_service.previous_week_entries()

        if title:
            st.subheader(title)

        if not current_entries:
            st.info(
                "No prediction history yet this week. Run a prediction to "
                "start building your weekly story."
            )
            return

        current_summary = history_service.summarize(current_entries)
        previous_summary = history_service.summarize(previous_entries) if previous_entries else None

        comparison_label = "vs. last week" if previous_summary else "this week"
        lines = cls._build_lines(current_summary, previous_summary, comparison_label)

        st.markdown(
            f"""
            <div style="
                padding: 20px 22px;
                border-radius: 14px;
                background: linear-gradient(135deg, rgba(56,142,60,0.08), rgba(25,118,210,0.06));
                border: 1px solid rgba(0,0,0,0.06);
            ">
                <p style="margin:0 0 10px 0; font-weight:600; opacity:0.75;">
                    {current_summary.start_date} → {current_summary.end_date}
                    ({current_summary.num_entries} day{'s' if current_summary.num_entries != 1 else ''} logged)
                </p>
                {''.join(f'<p style="margin:6px 0;">📌 {line}</p>' for line in lines)}
            </div>
            """,
            unsafe_allow_html=True,
        )
