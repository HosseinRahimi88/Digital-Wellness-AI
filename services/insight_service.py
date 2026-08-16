"""
Insight Service
------------------
Trust-and-context signals that sit *around* a prediction rather than
inside it (P1 items 13, 14, 17, 18):

  * Confidence Label      - plain-language reading of the model's own
                            probability + conformal uncertainty.
  * Out-of-Distribution   - flags an input that sits outside the range
                            the models were actually trained on, so a
                            confident-looking score on an implausible
                            day is labelled instead of trusted.
  * Cold-Start Policy     - how much of the app's history-dependent
                            output is trustworthy given how many days
                            the user has actually logged.
  * Day-of-Week Reliability - whether there is enough per-weekday data
                            to say anything about weekday patterns.

None of this changes a prediction. Every function is a pure read over
values the pipeline already produced (plus FEATURE_SCHEMA bounds), so
it can never alter the score it is describing.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional

from core.feature_schema import FEATURE_SCHEMA

# --- Cold-start thresholds -------------------------------------------
# Chosen to line up with what the downstream features actually need:
# a trend line needs a few points, weekday comparison needs repeats of
# the same weekday, and the weekly summaries group by ISO week.
COLD_START_STAGES = (
    (0, "no_data"),
    (1, "single_day"),
    (3, "early"),
    (7, "week"),
    (21, "established"),
)

# A weekday needs at least this many observations before its average is
# reported as a "pattern" rather than a single day's noise.
WEEKDAY_MIN_OBSERVATIONS = 2

# Fraction of a feature's schema range beyond which a value is treated
# as an extreme (still valid, but rare) observation.
_OOD_EDGE_FRACTION = 0.02

# Fields worth checking for out-of-distribution behaviour, each with the
# edge(s) that are genuinely implausible for that field.
#
# The direction matters and is not symmetric. Zero gaming minutes, zero
# caffeine and zero night-time screen use are all perfectly ordinary
# healthy days - flagging those as "out of distribution" would fire a
# scary warning on exactly the users doing best, which is worse than no
# warning at all. Only a maximum-edge value is implausible for those.
# A handful of fields are implausible at BOTH edges (nobody sleeps zero
# hours or uses a screen for zero minutes on a day they filled this in).
_OOD_WATCH_FIELDS: dict[str, str] = {
    "total_screen_min": "both",
    "social_min": "max",
    "gaming_min": "max",
    "video_min": "max",
    "night_screen_min": "max",
    "pre_sleep_screen_min": "max",
    "sleep_hours": "both",
    "notifications_per_day": "max",
    "pickups_per_day": "max",
    "app_opens_per_day": "max",
    "physical_activity_min_per_day": "max",
    "caffeine_cups_per_day": "max",
}


LANGUAGES = ("en", "fa", "ar", "zh")

# The plain-language confidence reading, in every shipped language.
#
# This paragraph sits directly under the score on the result screen and
# was English-only in all four - so a Persian or Arabic reader got a
# Persian page with an English explanation of how much to trust their own
# number, which is the last place to lose them.
#
# The wording stays deliberately conservative in every language: this
# project's own leakage-fixed evaluation showed the classifier is
# OVERCONFIDENT on genuinely new users (see LEAKAGE_FIX_REPORT), so a raw
# 85% is "reasonably confident" everywhere, never "very confident". A
# translation that upgraded the certainty would misstate the model.
_CONFIDENCE_HEADLINE: dict[str, dict[str, str]] = {
    "high": {
        "en": "The model is confident about this one.",
        "fa": "مدل درباره‌ی این یکی مطمئن است.",
        "ar": "النموذج واثق بشأن هذه النتيجة.",
        "zh": "模型对这个结果比较有把握。",
    },
    "moderate": {
        "en": "Reasonably confident, not certain.",
        "fa": "نسبتاً مطمئن، ولی قطعی نه.",
        "ar": "واثق إلى حدٍّ معقول، لكن ليس متيقناً.",
        "zh": "有一定把握，但并不确定。",
    },
    "low": {
        "en": "Treat this as a rough read.",
        "fa": "این را یک برآورد تقریبی در نظر بگیر.",
        "ar": "تعامل مع هذه النتيجة كقراءة تقريبية.",
        "zh": "请把这个结果当作粗略参考。",
    },
}

_CONFIDENCE_DETAIL: dict[str, dict[str, str]] = {
    "high": {
        "en": "Your inputs land clearly inside one wellness category.",
        "fa": "ورودی‌هایت به‌روشنی داخل یکی از دسته‌های سلامت می‌افتند.",
        "ar": "مدخلاتك تقع بوضوح داخل فئة واحدة من فئات العافية.",
        "zh": "你的输入清楚地落在某一个健康类别之内。",
    },
    "moderate": {
        "en": "Your inputs mostly point one way, with some overlap into a neighbouring category.",
        "fa": "ورودی‌هایت بیشتر به یک سمت اشاره می‌کنند، با کمی همپوشانی با دسته‌ی مجاور.",
        "ar": "مدخلاتك تشير في معظمها إلى اتجاه واحد، مع بعض التداخل مع فئة مجاورة.",
        "zh": "你的输入大体指向同一个方向，但与相邻类别有一些重叠。",
    },
    "low": {
        "en": "Your inputs sit close to the boundary between categories — the exact label could go either way.",
        "fa": "ورودی‌هایت نزدیک مرز بین دسته‌ها هستند — برچسب دقیق می‌تواند به هر طرف برود.",
        "ar": "مدخلاتك تقع قرب الحدّ الفاصل بين الفئات — والتصنيف الدقيق قد يميل إلى أيٍّ منهما.",
        "zh": "你的输入接近类别之间的边界——具体归入哪一类都有可能。",
    },
}

# Appended to the detail when conformal calibration produced an interval.
_CONFIDENCE_RANGE: dict[str, str] = {
    "en": " The likely score range spans about {points} points.",
    "fa": " بازه‌ی محتمل نمره حدود {points} امتیاز است.",
    "ar": " يمتد النطاق المرجّح للدرجة نحو {points} نقطة.",
    "zh": "可能的分数区间大约跨越 {points} 分。",
}


# The out-of-distribution warning, in every shipped language. Field
# labels inside {names} come from the feature schema and are substituted
# in unchanged.
_OOD_MESSAGE: dict[str, str] = {
    "en": ("Some of today's values sit at the very edge of what this model has seen "
           "({names}). The score is still computed from your real inputs, but treat it "
           "as less reliable than a typical day."),
    "fa": ("بعضی از مقادیر امروز درست لبه‌ی چیزی هستند که این مدل دیده است "
           "({names}). نمره همچنان از ورودی‌های واقعی خودت حساب می‌شود، ولی آن را "
           "کم‌اعتمادتر از یک روز معمولی در نظر بگیر."),
    "ar": ("بعض قيم اليوم تقع عند الحدّ الأقصى لما شاهده هذا النموذج "
           "({names}). ما زالت الدرجة محسوبة من مدخلاتك الحقيقية، لكن تعامل معها "
           "على أنها أقل موثوقية من يوم عادي."),
    "zh": ("今天的部分数值正处在该模型所见范围的最边缘"
           "（{names}）。分数仍然是根据你的真实输入计算的，但请把它视为"
           "比平常日子更不可靠。"),
}

# Which history-dependent views are meaningful yet, per cold-start stage.
_COLD_START_MESSAGE: dict[str, dict[str, str]] = {
    "no_data": {
        "en": "No check-ins yet. Your first one gives you a full score and explanation immediately — trends need a few more days.",
        "fa": "هنوز هیچ بررسی‌ای نداری. اولین بررسی بلافاصله نمره و توضیح کامل می‌دهد — روندها چند روز بیشتر لازم دارند.",
        "ar": "لا توجد فحوصات بعد. أول فحص يمنحك درجة وشرحاً كاملين فوراً — أما الاتجاهات فتحتاج أياماً إضافية.",
        "zh": "还没有任何记录。第一次记录会立刻给你完整的分数和解释——趋势则还需要几天。",
    },
    "single_day": {
        "en": "One check-in logged. Your score and its reasons are fully available; trends and weekday patterns need more days.",
        "fa": "یک بررسی ثبت شده. نمره و دلایلش کامل در دسترس‌اند؛ روندها و الگوهای روزهای هفته به روزهای بیشتری نیاز دارند.",
        "ar": "تم تسجيل فحص واحد. درجتك وأسبابها متاحة بالكامل؛ أما الاتجاهات وأنماط أيام الأسبوع فتحتاج أياماً أكثر.",
        "zh": "已记录一次。分数及其原因已完全可用；趋势和星期规律还需要更多天数。",
    },
    "early": {
        "en": "A few days logged. Trend direction is starting to mean something; weekday patterns still need repeats.",
        "fa": "چند روز ثبت شده. جهت روند کم‌کم معنا پیدا می‌کند؛ الگوهای روزهای هفته هنوز به تکرار نیاز دارند.",
        "ar": "تم تسجيل بضعة أيام. بدأ اتجاه المسار يعني شيئاً؛ وما زالت أنماط أيام الأسبوع تحتاج إلى تكرار.",
        "zh": "已记录几天。趋势方向开始有意义了；星期规律仍需要更多重复。",
    },
    "week": {
        "en": "About a week of history. Trends and week-over-week comparison are now meaningful.",
        "fa": "حدود یک هفته تاریخچه. روندها و مقایسه‌ی هفته‌به‌هفته حالا معنادار هستند.",
        "ar": "نحو أسبوع من السجل. الاتجاهات والمقارنة الأسبوعية صارت ذات معنى الآن.",
        "zh": "大约一周的历史。趋势和周与周之间的比较现在有意义了。",
    },
    "established": {
        "en": "Three weeks or more logged. Every trend, weekday and before/after view here is on solid ground.",
        "fa": "سه هفته یا بیشتر ثبت شده. هر روند، هر روز هفته و هر نمای قبل/بعد اینجا پایه‌ی محکمی دارد.",
        "ar": "ثلاثة أسابيع أو أكثر من التسجيل. كل اتجاه ويوم أسبوع وعرض قبل/بعد هنا يقوم على أساس متين.",
        "zh": "已记录三周或更久。这里的每一项趋势、星期和前后对比都有扎实的基础。",
    },
}


@dataclass(slots=True)
class ConfidenceLabel:
    level: str          # "high" | "moderate" | "low"
    percent: float
    headline: str
    detail: str
    interval_width: Optional[float] = None
    # The same headline/detail in every shipped language, as
    # {part: {lang: text}}. `headline`/`detail` above stay English so no
    # existing caller changes; the UI reads this and falls back to them.
    # Same arrangement RecommendationResponse.text_i18n already uses.
    text_i18n: dict = field(default_factory=dict)


@dataclass(slots=True)
class OODFlag:
    field_name: str
    label: str
    value: float
    minimum: float
    maximum: float
    position: str       # "at_or_below_minimum" | "at_or_above_maximum"


@dataclass(slots=True)
class OODReport:
    is_out_of_distribution: bool
    flags: list[OODFlag] = field(default_factory=list)
    message: str = ""
    # {part: {lang: text}} - the same message in every shipped
    # language. `message` above stays English for older clients.
    text_i18n: dict = field(default_factory=dict)


@dataclass(slots=True)
class ColdStartStatus:
    entry_count: int
    stage: str
    trend_available: bool
    weekday_pattern_available: bool
    week_comparison_available: bool
    message: str
    # {part: {lang: text}} - the same message in every shipped
    # language. `message` above stays English for older clients.
    text_i18n: dict = field(default_factory=dict)


@dataclass(slots=True)
class WeekdayReliability:
    weekday: str
    observations: int
    average_score: Optional[float]
    is_reliable: bool


class InsightService:

    # ------------------------------------------------------------
    # Confidence label (P1 item 17)
    # ------------------------------------------------------------

    @staticmethod
    def confidence_label(
        confidence_percent: Optional[float],
        uncertainty: Optional[Any] = None,
    ) -> ConfidenceLabel:
        """
        Turn the raw probability (and conformal interval, when
        calibration succeeded) into something a non-specialist can act
        on. The thresholds are deliberately conservative: this project's
        own leakage-fixed evaluation showed the classifier is
        *overconfident* on genuinely new users (see LEAKAGE_FIX_REPORT),
        so a raw 85% is described as "reasonably confident", never
        "very confident".
        """
        pct = float(confidence_percent or 0.0)
        width = None
        if uncertainty is not None:
            width = getattr(uncertainty, "regression_interval_width", None)
            if width is None and isinstance(uncertainty, dict):
                width = uncertainty.get("regression_interval_width")

        if pct >= 90:
            level = "high"
        elif pct >= 70:
            level = "moderate"
        else:
            level = "low"

        headline_all = dict(_CONFIDENCE_HEADLINE[level])
        detail_all = dict(_CONFIDENCE_DETAIL[level])

        # The interval sentence is appended in every language, not just
        # English - a Persian reader was getting a Persian-looking
        # paragraph that ended in an English clause about their score.
        if width is not None:
            points = round(float(width))
            for lang in LANGUAGES:
                detail_all[lang] = detail_all[lang] + _CONFIDENCE_RANGE[lang].format(points=points)

        return ConfidenceLabel(
            level=level, percent=round(pct, 2),
            headline=headline_all["en"], detail=detail_all["en"],
            interval_width=round(float(width), 2) if width is not None else None,
            text_i18n={"headline": headline_all, "detail": detail_all},
        )

    # ------------------------------------------------------------
    # Out-of-distribution warning (P1 item 18)
    # ------------------------------------------------------------

    @staticmethod
    def check_out_of_distribution(user_data: dict[str, Any]) -> OODReport:
        """
        Flags inputs pinned at (or past) the edge of their schema range.

        Why the schema range and not the training data's empirical
        distribution: the raw training CSVs are not shipped with this
        repo (see .gitignore), so an empirical percentile check would
        silently do nothing wherever the data is absent - a guard that
        quietly stops guarding is worse than a simpler one that always
        works. FEATURE_SCHEMA's bounds ARE the declared valid domain, so
        sitting at the very edge of one is the honest, always-available
        signal that this day is unlike a typical modelled day.
        """
        flags: list[OODFlag] = []

        for field_name, watch in _OOD_WATCH_FIELDS.items():
            feature = FEATURE_SCHEMA.get(field_name)
            if feature is None or feature.minimum is None or feature.maximum is None:
                continue
            raw = user_data.get(field_name)
            if raw is None:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue

            lo, hi = float(feature.minimum), float(feature.maximum)
            span = hi - lo
            if span <= 0:
                continue
            edge = span * _OOD_EDGE_FRACTION

            if watch in ("max", "both") and value >= hi - edge:
                position = "at_or_above_maximum"
            elif watch in ("min", "both") and value <= lo + edge:
                position = "at_or_below_minimum"
            else:
                continue

            flags.append(OODFlag(
                field_name=field_name, label=feature.label or field_name,
                value=value, minimum=lo, maximum=hi, position=position,
            ))

        if not flags:
            return OODReport(is_out_of_distribution=False, flags=[], message="")

        names = ", ".join(f.label for f in flags[:3])
        message_all = {
            lang: text.format(names=names) for lang, text in _OOD_MESSAGE.items()
        }
        return OODReport(
            is_out_of_distribution=True, flags=flags,
            message=message_all["en"], text_i18n={"message": message_all},
        )

    # ------------------------------------------------------------
    # Cold-start policy (P1 item 13)
    # ------------------------------------------------------------

    @staticmethod
    def cold_start_status(entry_count: int) -> ColdStartStatus:
        """
        States plainly which history-dependent features are meaningful
        yet. Single-day predictions always work - it's the *trend*
        features that need history, and saying so up front is better
        than rendering an empty chart with no explanation.
        """
        stage = "no_data"
        for threshold, name in COLD_START_STAGES:
            if entry_count >= threshold:
                stage = name

        message_all = dict(_COLD_START_MESSAGE[stage])

        return ColdStartStatus(
            entry_count=entry_count,
            stage=stage,
            trend_available=entry_count >= 3,
            weekday_pattern_available=entry_count >= 7,
            week_comparison_available=entry_count >= 7,
            message=message_all["en"],
            text_i18n={"message": message_all},
        )

    # ------------------------------------------------------------
    # Day-of-week reliability (P1 item 14)
    # ------------------------------------------------------------

    @staticmethod
    def weekday_reliability(entries: list[dict[str, Any]]) -> list[WeekdayReliability]:
        """
        Per-weekday averages annotated with how many observations back
        them. A weekday seen once gets `is_reliable=False` and the UI is
        expected to de-emphasise it rather than present one Tuesday as
        "your Tuesdays".
        """
        counts: Counter = Counter()
        totals: dict[str, float] = {}

        for entry in entries:
            weekday = entry.get("day_of_week")
            score = entry.get("health_score")
            if not weekday or score is None:
                continue
            try:
                value = float(score)
            except (TypeError, ValueError):
                continue
            counts[weekday] += 1
            totals[weekday] = totals.get(weekday, 0.0) + value

        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        result: list[WeekdayReliability] = []
        for weekday in order:
            n = counts.get(weekday, 0)
            avg = round(totals[weekday] / n, 2) if n else None
            result.append(WeekdayReliability(
                weekday=weekday, observations=n, average_score=avg,
                is_reliable=n >= WEEKDAY_MIN_OBSERVATIONS,
            ))
        return result
