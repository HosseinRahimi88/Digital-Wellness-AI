"""
Risk Alert Service
--------------------
Small, rule-based helper (same pattern as services/achievement_service.py)
that surfaces "Critical Risk Alerts" from a user's real HistoryService
entries - no model logic, no LLM, nothing invented. Three independent,
composable rules, each grounded in data the pipeline already produced:

1. Classification risk: the model's own real `health_class` output was
   "At Risk" on the latest check-in, escalated to "critical" severity
   if it's part of a real consecutive streak.
2. Trend risk: a real multi-check-in decline in `health_score`.
3. Deviation risk: reuses AnalyticsService.detect_exception_days (29's
   personal-baseline z-score statistic) to flag when the latest
   check-in itself was a real negative outlier for this specific user
   - deliberately reused rather than re-implemented, so there is only
   one place "what counts as an exception" is decided.

This never touches models/, artifacts/, or PredictionService/SHAPService
- it only reads fields HistoryService already persisted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from services.analytics_service import AnalyticsService
from services.report_i18n import FIELD_LABELS

LANGUAGES = ("en", "fa", "ar", "zh")

# The model's own class names, translated once here rather than per
# alert - kept in sync by eye with games.js's futureClassGuess CLASSES
# table, which is the other place a reader sees these three words.
_CLASS_LABEL_I18N: dict[str, dict[str, str]] = {
    "At Risk": {"en": "At Risk", "fa": "در معرض خطر", "ar": "في خطر", "zh": "有风险"},
    "Healthy": {"en": "Healthy", "fa": "سالم", "ar": "صحي", "zh": "健康"},
    "Moderate": {"en": "Moderate", "fa": "متوسط", "ar": "متوسط", "zh": "中等"},
}


def _class_label_i18n(class_name: str) -> dict[str, str]:
    return _CLASS_LABEL_I18N.get(class_name, {lang: class_name for lang in LANGUAGES})


def _field_label_i18n(field_name: str) -> dict[str, str]:
    return FIELD_LABELS.get(field_name, {lang: field_name for lang in LANGUAGES})


def _text_i18n(templates: dict[str, str], **kwargs: Any) -> dict[str, str]:
    """Fill a {lang: template} table with the same kwargs in every
    language - the same .format() convention improvement_plan_service
    and tone_service already use, so alert text is built the identical
    way every other server-composed sentence in this app is."""
    return {lang: template.format(**kwargs) for lang, template in templates.items()}


# The model's own real classification label for the at-risk class (see
# services/prediction_service.py::PredictionService.CLASS_MAPPING) -
# not re-typed as a magic string anywhere else in this file.
AT_RISK_CLASS_LABEL = "At Risk"

# A streak of at least this many consecutive At-Risk check-ins escalates
# from "warning" to "critical" severity.
CONSECUTIVE_AT_RISK_FOR_CRITICAL = 2

# A decline streak needs at least this many consecutive check-ins,
# each strictly lower than the last, AND a total drop of at least this
# many points, before it's flagged - short/small dips are normal noise.
DECLINE_STREAK_LENGTH = 3
DECLINE_STREAK_MIN_TOTAL_DROP = 10.0

_TITLES = {
    "consecutive_at_risk": {
        "en": "Consecutive At-Risk Check-ins", "fa": "بررسی‌های پیاپیِ «در معرض خطر»",
        "ar": "فحوصات متتالية في خطر", "zh": "连续多次「有风险」检测",
    },
    "latest_at_risk": {
        "en": "Latest Check-in: At Risk", "fa": "آخرین بررسی: در معرض خطر",
        "ar": "أحدث فحص: في خطر", "zh": "最近一次检测：有风险",
    },
    "declining_trend": {
        "en": "Declining Trend", "fa": "روند نزولی",
        "ar": "اتجاه متراجع", "zh": "下降趋势",
    },
    "unusual_day": {
        "en": "Unusual Day Detected", "fa": "روز غیرعادی شناسایی شد",
        "ar": "تم رصد يوم غير معتاد", "zh": "检测到异常的一天",
    },
}

_MESSAGES = {
    "consecutive_at_risk": {
        "en": "Your last {streak} check-ins were all classified \"{class_label}\" by the model.",
        "fa": "آخرین {streak} بررسی‌ات همگی توسط مدل «{class_label}» طبقه‌بندی شدند.",
        "ar": "آخر {streak} فحوصات لك صُنِّفت جميعها بأنها \"{class_label}\" من قِبل النموذج.",
        "zh": "你最近 {streak} 次检测都被模型判定为「{class_label}」。",
    },
    "latest_at_risk": {
        "en": "Your most recent check-in ({date}) was classified \"{class_label}\"{conf}.",
        "fa": "آخرین بررسی‌ات ({date}) «{class_label}» طبقه‌بندی شد{conf}.",
        "ar": "آخر فحص لك ({date}) صُنِّف بأنه \"{class_label}\"{conf}.",
        "zh": "你最近一次检测（{date}）被判定为「{class_label}」{conf}。",
    },
    "declining_trend": {
        "en": "Your wellness score has dropped for {length} check-ins in a row ({start} → {end}).",
        "fa": "امتیاز سلامتت طیِ {length} بررسیِ پیاپی افت کرده ({start} → {end}).",
        "ar": "انخفضت درجة عافيتك خلال {length} فحوصات متتالية ({start} → {end}).",
        "zh": "你的健康分已连续 {length} 次检测下降（{start} → {end}）。",
    },
    "unusual_day": {
        "en": "Today's {field_label} ({value}) is {z} standard deviations below your typical {typical}.",
        "fa": "{field_label} امروزت ({value})، {z} انحراف معیار پایین‌تر از حالت معمولت ({typical}) است.",
        "ar": "{field_label} اليوم ({value}) أقل بمقدار {z} انحرافاً معيارياً عن معدّلك المعتاد ({typical}).",
        "zh": "你今天的{field_label}（{value}）比你的日常水平（{typical}）低了 {z} 个标准差。",
    },
}

_ACTIONS = {
    "consecutive_at_risk": {
        "en": "Review the factors driving this in \"What's Driving Your Score\" below, and consider talking to someone you trust or a professional if this continues.",
        "fa": "عوامل پشتِ این را در «چه چیزی امتیازت را می‌سازد» پایین‌تر ببین، و اگر ادامه پیدا کرد، صحبت با کسی که بهش اعتماد داری یا یک متخصص را در نظر بگیر.",
        "ar": "راجع العوامل الكامنة وراء هذا في \"ما الذي يحرّك درجتك\" أدناه، وفكّر في التحدث إلى شخص تثق به أو مختص إن استمر الأمر.",
        "zh": "在下方的「是什么在影响你的分数」里查看背后的原因，如果这种情况持续，考虑和你信任的人或专业人士谈谈。",
    },
    "latest_at_risk": {
        "en": "Check the factors behind this in \"What's Driving Your Score\".",
        "fa": "عوامل پشتِ این را در «چه چیزی امتیازت را می‌سازد» ببین.",
        "ar": "تحقّق من العوامل وراء هذا في \"ما الذي يحرّك درجتك\".",
        "zh": "在「是什么在影响你的分数」里查看背后的原因。",
    },
    "declining_trend": {
        "en": "Worth watching closely before it becomes a longer pattern.",
        "fa": "ارزش دارد از نزدیک زیرِ نظر بگیری‌اش پیش از آنکه به یک الگوی طولانی‌تر تبدیل شود.",
        "ar": "يستحق المراقبة عن كثب قبل أن يتحول إلى نمط أطول أمداً.",
        "zh": "值得密切关注，别让它变成更长期的模式。",
    },
}

_CONFIDENCE_WRAP = {
    "en": " ({pct}% confidence)", "fa": " (اطمینان {pct}٪)",
    "ar": " (بثقة {pct}٪)", "zh": "（置信度 {pct}%）",
}


@dataclass(slots=True)
class RiskAlert:
    severity: str  # "critical" | "warning" | "info"
    title: str
    message: str
    action: Optional[str] = None
    # {"title": {lang: text}, "message": {lang: text}, "action": {lang: text}}
    # - "action" is omitted entirely when there is none, so a client
    # checking `text_i18n.get("action")` sees the same None-ness the
    # flat `action` field already carries, in every language at once.
    text_i18n: dict[str, dict[str, str]] = field(default_factory=dict)


class RiskAlertService:
    """Evaluates a user's real check-in history for risk signals."""

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

    @staticmethod
    def _trailing_class_streak(ordered_entries: list[dict[str, Any]], class_label: str) -> int:
        """How many of the most recent entries, counting back from the
        end, have health_class == class_label (stops at the first
        entry that doesn't match, or at a missing health_class)."""
        streak = 0
        for entry in reversed(ordered_entries):
            if entry.get("health_class") != class_label:
                break
            streak += 1
        return streak

    @staticmethod
    def _detect_decline_streak(ordered_entries: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """The longest strictly-decreasing run of health_score ending at
        the most recent entry, if it's at least DECLINE_STREAK_LENGTH
        long and drops at least DECLINE_STREAK_MIN_TOTAL_DROP points in
        total. None otherwise (including when scores are missing)."""
        scores = [e.get("health_score") for e in ordered_entries]
        if any(s is None for s in scores[-DECLINE_STREAK_LENGTH:]) or len(scores) < DECLINE_STREAK_LENGTH:
            return None

        run = [scores[-1]]
        for value in reversed(scores[:-1]):
            if value is None:
                break
            if value > run[-1]:
                run.append(value)
            else:
                break
        run.reverse()  # oldest -> newest

        if len(run) < DECLINE_STREAK_LENGTH:
            return None

        total_drop = run[0] - run[-1]
        if total_drop < DECLINE_STREAK_MIN_TOTAL_DROP:
            return None

        return {"length": len(run), "start_score": run[0], "end_score": run[-1]}

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    @classmethod
    def evaluate(cls, entries: list[dict[str, Any]]) -> list[RiskAlert]:
        """
        Returns a list of active RiskAlerts for this user's real
        history, most severe first. Empty list means no active risk
        signal (a good state to render as reassuring, not just absent).
        """
        if not entries:
            return []

        ordered = sorted(entries, key=lambda e: e.get("date", ""))
        latest = ordered[-1]
        alerts: list[RiskAlert] = []

        class_label_i18n = _class_label_i18n(AT_RISK_CLASS_LABEL)

        # --- Rule 1: classification risk -------------------------------
        if latest.get("health_class") == AT_RISK_CLASS_LABEL:
            streak = cls._trailing_class_streak(ordered, AT_RISK_CLASS_LABEL)
            if streak >= CONSECUTIVE_AT_RISK_FOR_CRITICAL:
                alerts.append(RiskAlert(
                    severity="critical",
                    title="Consecutive At-Risk Check-ins",
                    message=(
                        f"Your last {streak} check-ins were all classified "
                        f"\"{AT_RISK_CLASS_LABEL}\" by the model."
                    ),
                    action=(
                        "Review the factors driving this in \"What's Driving Your "
                        "Score\" below, and consider talking to someone you trust "
                        "or a professional if this continues."
                    ),
                    text_i18n={
                        "title": dict(_TITLES["consecutive_at_risk"]),
                        "message": {
                            lang: _MESSAGES["consecutive_at_risk"][lang].format(
                                streak=streak, class_label=class_label_i18n[lang],
                            )
                            for lang in LANGUAGES
                        },
                        "action": dict(_ACTIONS["consecutive_at_risk"]),
                    },
                ))
            else:
                confidence = latest.get("confidence")
                conf_text = f" ({confidence:.0%} confidence)" if confidence is not None else ""
                conf_pct = round(confidence * 100) if confidence is not None else None
                conf_i18n = (
                    {lang: tpl.format(pct=conf_pct) for lang, tpl in _CONFIDENCE_WRAP.items()}
                    if conf_pct is not None else {lang: "" for lang in LANGUAGES}
                )
                alerts.append(RiskAlert(
                    severity="warning",
                    title="Latest Check-in: At Risk",
                    message=(
                        f"Your most recent check-in ({latest.get('date', 'unknown date')}) "
                        f"was classified \"{AT_RISK_CLASS_LABEL}\"{conf_text}."
                    ),
                    action="Check the factors behind this in \"What's Driving Your Score\".",
                    text_i18n={
                        "title": dict(_TITLES["latest_at_risk"]),
                        "message": {
                            lang: _MESSAGES["latest_at_risk"][lang].format(
                                date=latest.get("date", "unknown date"),
                                class_label=class_label_i18n[lang],
                                conf=conf_i18n[lang],
                            )
                            for lang in LANGUAGES
                        },
                        "action": dict(_ACTIONS["latest_at_risk"]),
                    },
                ))

        # --- Rule 2: trend risk ------------------------------------------
        decline = cls._detect_decline_streak(ordered)
        if decline is not None:
            alerts.append(RiskAlert(
                severity="warning",
                title="Declining Trend",
                message=(
                    f"Your wellness score has dropped for {decline['length']} "
                    f"check-ins in a row ({decline['start_score']:.1f} → "
                    f"{decline['end_score']:.1f})."
                ),
                action="Worth watching closely before it becomes a longer pattern.",
                text_i18n={
                    "title": dict(_TITLES["declining_trend"]),
                    "message": _text_i18n(
                        _MESSAGES["declining_trend"],
                        length=decline["length"],
                        start=f"{decline['start_score']:.1f}",
                        end=f"{decline['end_score']:.1f}",
                    ),
                    "action": dict(_ACTIONS["declining_trend"]),
                },
            ))

        # --- Rule 3: deviation risk (reuses AnalyticsService, doesn't
        # re-derive its own z-score logic) ---------------------------
        exceptions = AnalyticsService.detect_exception_days(ordered)
        if exceptions:
            latest_date = latest.get("date")
            latest_exception = next((e for e in exceptions if e["date"] == latest_date), None)
            if latest_exception and latest_exception["deviations"]:
                worst = latest_exception["deviations"][0]
                if worst["z_score"] < 0:
                    field_label_i18n = _field_label_i18n(worst["field"])
                    alerts.append(RiskAlert(
                        severity="info",
                        title="Unusual Day Detected",
                        message=(
                            f"Today's {worst['label']} ({worst['value']}) is "
                            f"{abs(worst['z_score']):.1f} standard deviations below "
                            f"your typical {worst['typical']}."
                        ),
                        action=None,
                        text_i18n={
                            "title": dict(_TITLES["unusual_day"]),
                            "message": {
                                lang: _MESSAGES["unusual_day"][lang].format(
                                    field_label=field_label_i18n[lang],
                                    value=worst["value"],
                                    z=f"{abs(worst['z_score']):.1f}",
                                    typical=worst["typical"],
                                )
                                for lang in LANGUAGES
                            },
                        },
                    ))

        severity_rank = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda a: severity_rank.get(a.severity, 3))
        return alerts
