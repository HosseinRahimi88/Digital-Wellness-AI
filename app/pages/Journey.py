"""
Journey Page

Houses the Group A product/UX features that are about the user's
whole journey rather than a single check-in or a single week:
Journey Summary, Score Battery, Healthy Streak, Level/Progress,
Sparkline trends, Achievement Badges, Opportunity Cost / "Three Lost
Days", the Improvement Chain view of this week's plan, and Future
Letters.

Everything here is built from real HistoryService entries (themselves
built from real PredictionService/SHAPService output) plus the
existing ImprovementPlanService/PlanProgressService - no new ML logic,
no new prediction/recommendation logic. See services/gamification_service.py,
services/opportunity_cost_service.py, and services/letter_service.py
for where the actual computation lives; this page only renders it.
"""
import streamlit as st
import bootstrap

st.set_page_config(
    page_title="Journey",
    page_icon="🧭",
    layout="wide",
)

from components.theme import Theme
Theme.load()

from services.history_service import HistoryService
from services.improvement_plan_service import ImprovementPlanService
from services.plan_progress_service import PlanProgressService
from services.letter_service import LetterService
from services.commitment_service import CommitmentService, STATUS_ACTIVE, STATUS_ABANDONED, STATUS_COMPLETED
from services.recommendation_effectiveness_service import (
    CATEGORY_PRIMARY_FIELD,
    RecommendationEffectivenessService,
)
from services.analytics_service import AnalyticsService
from services.cohort_service import CohortService
from services.leaderboard_service import LeaderboardService
from services.rare_achievement_service import RareAchievementService
from services.weekly_challenge_service import WeeklyChallengeService
from services.focus_coins_service import FocusCoinsService
from config.analytics_settings import BEHAVIORAL_FIELD_LABELS
from utils.session import (
    get_last_persona,
    get_last_prediction_result,
    get_last_user_data,
    get_user_id,
)

from components.dynamic_background import DynamicBackground
from components.animated_guide import AnimatedGuide
from components.journey_summary_card import JourneySummaryCard
from components.score_battery import ScoreBattery
from components.streak_tracker import StreakTracker
from components.level_progress import LevelProgress
from components.sparkline import Sparkline
from components.badges_card import BadgesCard
from components.metric_card import MetricCard
from components.opportunity_cost_card import OpportunityCostCard
from components.improvement_chain import ImprovementChain
from components.future_letter_card import FutureLetterCard
from components.text_to_speech import TextToSpeech

st.title("🧭 Your Journey")
st.write(
    "A whole-journey view of your real digital wellness history - "
    "streaks, levels, badges, and long-term trends, all built from "
    "check-ins you've actually run."
)

history_service = HistoryService(user_id=get_user_id())
all_entries = history_service.get_all()

if not all_entries:
    st.info(
        "Your journey starts with one check-in. Run a prediction "
        "(a real one, or a Quick Demo profile) to unlock this page."
    )
    if st.button("🚀 Run a Check-in", type="primary"):
        st.switch_page("pages/Prediction.py")
    st.stop()

latest_entry = all_entries[-1]

DynamicBackground.apply(latest_entry.get("health_score"))

AnimatedGuide.render(
    guide_id="journey_page",
    title="👋 New here?",
    steps=[
        "This page tracks your whole journey, not just one check-in - your streak, level, and badges live here.",
        "The battery and sparkline show your latest score and its recent trend at a glance.",
        "Scroll down for the Opportunity Cost view and a letter you can seal for your future self.",
    ],
)

st.divider()

# ------------------------------------------------------------
# Journey Summary
# ------------------------------------------------------------
JourneySummaryCard.render(all_entries)

st.divider()

# ------------------------------------------------------------
# Score Battery + Sparkline + Streak + Level
# ------------------------------------------------------------
col_battery, col_trend = st.columns([1, 2])
with col_battery:
    ScoreBattery.render(latest_entry.get("health_score"))
with col_trend:
    Sparkline.render(all_entries, field_name="health_score", title="📈 Score Trend (all time)")

col_streak, col_level = st.columns(2)
with col_streak:
    StreakTracker.render(all_entries)
with col_level:
    LevelProgress.render(all_entries)

st.divider()

# ------------------------------------------------------------
# Focus Coins (17) - a virtual currency computed fresh each render
# from real actions only (check-ins, streak, completed plan tasks,
# completed commitments, unlocked badges) - see
# services/focus_coins_service.py for why this is never a persisted,
# independently-mutable balance.
# ------------------------------------------------------------
_commitment_service = CommitmentService(user_id=get_user_id())
_all_commitments = _commitment_service.get_all()
_completed_commitments_count = sum(1 for c in _all_commitments if c.status == STATUS_COMPLETED)

_plan_progress_for_coins = PlanProgressService(user_id=get_user_id())
_completed_plan_tasks_count = len(_plan_progress_for_coins.get_completed())

_coins_balance = FocusCoinsService.compute_balance(
    all_entries,
    completed_plan_tasks=_completed_plan_tasks_count,
    completed_commitments=_completed_commitments_count,
)

st.subheader("🪙 Focus Coins")
_coin_col1, _coin_col2, _coin_col3, _coin_col4, _coin_col5 = st.columns(5)
with _coin_col1:
    MetricCard.render(title="🪙 Total", value=str(_coins_balance.total))
with _coin_col2:
    MetricCard.render(title="Check-ins", value=f"+{_coins_balance.from_checkins}")
with _coin_col3:
    MetricCard.render(title="Streak Bonus", value=f"+{_coins_balance.from_streak}")
with _coin_col4:
    MetricCard.render(title="Plan Tasks", value=f"+{_coins_balance.from_plan_tasks}")
with _coin_col5:
    MetricCard.render(title="Commitments", value=f"+{_coins_balance.from_commitments}")

st.divider()

# ------------------------------------------------------------
# Achievement Badges
# ------------------------------------------------------------
BadgesCard.render(all_entries)

st.divider()

# ------------------------------------------------------------
# Weekly Challenges (16) - personalized targets derived from this
# user's own real baselines (AnalyticsService), evaluated against the
# current ISO week's real entries.
# ------------------------------------------------------------
st.subheader("🏁 This Week's Challenges")
_challenges = WeeklyChallengeService.generate_challenges(all_entries)
for _challenge in _challenges:
    _status_icon = "✅" if _challenge.completed else "⏳"
    st.write(f"{_status_icon} {_challenge.icon} **{_challenge.title}** — {_challenge.description}")
    st.progress(min(_challenge.progress / _challenge.target, 1.0) if _challenge.target else 0.0)

st.divider()

# ------------------------------------------------------------
# Commitment Tracking (41) + Recommendation Effectiveness (13) +
# Recommendation Learning Loop (56) - real commitments, evaluated
# against real before/after HistoryService averages. The Learning
# Loop itself (using this data to bias future recommendation order)
# runs silently on the Prediction page - this section is where its
# real, measured input comes from and is shown transparently.
# ------------------------------------------------------------
st.subheader("🤝 Commitments & Recommendation Effectiveness")
st.caption(
    "Commit to a recommendation category, and Digital Wellness AI will "
    "measure whether your real recorded scores actually improved "
    "afterward - and use that to favor what's worked for you before."
)

_active_commitments = [c for c in _all_commitments if c.status == STATUS_ACTIVE]

_commit_col1, _commit_col2 = st.columns([2, 1])
with _commit_col1:
    _new_category = st.selectbox(
        "Commit to a category",
        options=list(CATEGORY_PRIMARY_FIELD.keys()),
        key="journey_commit_category",
    )
with _commit_col2:
    st.write("")
    st.write("")
    if st.button("✅ Commit", key="journey_commit_button", use_container_width=True):
        _commitment_service.commit(_new_category)
        st.rerun()

if _active_commitments:
    st.markdown("**Active commitments**")
    for _c in _active_commitments:
        _acol1, _acol2, _acol3 = st.columns([3, 1, 1])
        with _acol1:
            st.write(f"🎯 **{_c.category}** — since {_c.committed_on}")
        with _acol2:
            if st.button("Done", key=f"resolve_done_{_c.commitment_id}"):
                _commitment_service.resolve(_c.commitment_id, STATUS_COMPLETED)
                st.rerun()
        with _acol3:
            if st.button("Abandon", key=f"resolve_abandon_{_c.commitment_id}"):
                _commitment_service.resolve(_c.commitment_id, STATUS_ABANDONED)
                st.rerun()

_effectiveness_results = RecommendationEffectivenessService.evaluate_all(_all_commitments, all_entries)
if _effectiveness_results:
    st.markdown("**Effectiveness of past commitments**")
    for _res in _effectiveness_results:
        if _res.verdict == "insufficient_data":
            _verdict_text = "⏳ Not enough data yet to tell"
        elif _res.verdict == "improved":
            _verdict_text = f"📈 Improved (score {_res.before_avg_score} → {_res.after_avg_score})"
        elif _res.verdict == "declined":
            _verdict_text = f"📉 Declined (score {_res.before_avg_score} → {_res.after_avg_score})"
        else:
            _verdict_text = f"➖ No measurable change (score {_res.before_avg_score} → {_res.after_avg_score})"
        st.write(f"- **{_res.category}** (committed {_res.committed_on}): {_verdict_text}")
else:
    st.caption("No commitments yet - pick a category above to start tracking real effectiveness.")

st.divider()

# ------------------------------------------------------------
# Cohort Comparison (35) + Reverse Leaderboard (31) + Rare
# Achievement System (20) - all built from this user's real
# historical averages compared against the real training dataset
# (services/cohort_service.py), plus RareAchievementService's real
# streak-based tier. No synthetic cohort or fabricated percentiles.
# ------------------------------------------------------------
st.subheader("🌍 How You Compare & Rare Achievements")

_user_averages = AnalyticsService.compute_field_averages(all_entries)

if not CohortService.is_available():
    st.caption("Cohort comparison data isn't available in this environment.")
else:
    _cohort_tab, _leaderboard_tab, _rare_tab = st.tabs(
        ["🌍 Cohort Comparison", "🔁 Reverse Leaderboard", "👑 Rare Achievements"]
    )

    with _cohort_tab:
        _cohort_rows = CohortService.compare_user_to_cohort(_user_averages)
        if not _cohort_rows:
            st.caption("Log a few more check-ins to unlock cohort comparison.")
        else:
            st.caption(
                f"Compared against {CohortService.cohort_size():,} real records from the "
                f"model's own training population."
            )
            for _row in _cohort_rows:
                _label = BEHAVIORAL_FIELD_LABELS.get(_row["field"], _row["field"])
                st.write(
                    f"- **{_label}**: your average is **{_row['user_value']}** — "
                    f"that's the {_row['cohort_percentile']:.0f}th percentile "
                    f"(cohort average: {_row['cohort_mean']})"
                )

    with _leaderboard_tab:
        st.caption(
            "For habits where *less* is healthier, this reframes your real "
            "percentile as a rank - a low raw number becomes a high rank."
        )
        _leaderboard_rows = LeaderboardService.compute_reverse_leaderboard(_user_averages)
        if not _leaderboard_rows:
            st.caption("Log a few more check-ins to unlock the reverse leaderboard.")
        else:
            for _row in _leaderboard_rows:
                st.write(
                    f"- **{_row['label']}**: you have less than "
                    f"**{_row['better_than_pct']:.0f}%** of the training population "
                    f"(≈{_row['rank_estimate']:,} people, average {_row['user_value']})"
                )

    with _rare_tab:
        _rare_achievements = RareAchievementService.compute_rare_achievements(_user_averages, all_entries)
        if not _rare_achievements:
            st.caption(
                "No rare-tier achievements yet - these are statistically "
                "uncommon (top ~10% or better against real data), so they "
                "may take time to unlock."
            )
        else:
            for _ra in _rare_achievements:
                st.markdown(f"{_ra.icon} **{_ra.name}** _( {_ra.tier} )_")
                st.caption(_ra.description)

st.divider()

# ------------------------------------------------------------
# Opportunity Cost / Three Lost Days (last 7 logged days)
# ------------------------------------------------------------
last_7_days = history_service.get_last_n_days(n=7)
last_7_entries = [d["entry"] for d in last_7_days if d.get("entry")]
OpportunityCostCard.render(last_7_entries)

st.divider()

# ------------------------------------------------------------
# Improvement Chain (this week's plan, visual summary)
# ------------------------------------------------------------
st.subheader("🔗 This Week's Plan at a Glance")

_session_result = get_last_prediction_result()
_session_user_data = get_last_user_data()
_session_persona = get_last_persona()

if _session_result is not None:
    _plan_health_class = _session_result.prediction
    _plan_wellness_score = _session_result.regression_score
    _plan_persona = _session_persona
    _plan_user_data = _session_user_data or {}
else:
    _plan_health_class = latest_entry.get("health_class")
    _plan_wellness_score = latest_entry.get("health_score")
    _plan_persona = latest_entry.get("persona")
    _plan_user_data = latest_entry

_weekly_plan = ImprovementPlanService().generate(
    health_class=_plan_health_class,
    wellness_score=_plan_wellness_score,
    persona=_plan_persona,
    user_data=_plan_user_data,
)
_progress_service = PlanProgressService(user_id=get_user_id())
ImprovementChain.render(_weekly_plan, _progress_service)
st.caption("Check off tasks on the Weekly Insights page - this chain reflects that same saved progress.")
if st.button("📅 Go to Weekly Plan"):
    st.switch_page("pages/Weekly_Insights.py")

st.divider()

# ------------------------------------------------------------
# Weekly story, read aloud (Text-to-Speech)
# ------------------------------------------------------------
st.subheader("🗞️ Your Story, Read Aloud")
_story_lines = []
_current_week_summary = history_service.summarize(history_service.current_week_entries())
if _current_week_summary and _current_week_summary.avg_health_score is not None:
    _story_text = (
        f"This week your average digital wellness score was "
        f"{_current_week_summary.avg_health_score:.1f} out of 100, "
        f"across {_current_week_summary.num_entries} logged day(s)."
    )
    TextToSpeech.render(_story_text)
    st.caption(_story_text)
else:
    st.info("Log a check-in this week to unlock a story you can listen to.")

st.divider()

# ------------------------------------------------------------
# Future Letter
# ------------------------------------------------------------
_letter_service = LetterService(user_id=get_user_id())
FutureLetterCard.render(_letter_service, current_score=latest_entry.get("health_score"))
