"""
Tone Service
---------------
P1 item 20: three voices for the same advice.

Hard rule this module exists to enforce: tone changes *wording only*.
The recommendation set, its priority order, the success metric and the
safety note are produced by RecommendationService from real SHAP output
and are passed through untouched. Rephrasing must never soften a HIGH
priority into sounding optional, or turn a LOW one into an alarm - so
the priority label itself is never rewritten here.

Tones:
  gentle   - encouraging, low-pressure. Default.
  direct   - blunt and specific. Directness, never shaming (the product
             brief's explicit red line).
  clinical - neutral and factual, no second person cheerleading.
"""

from __future__ import annotations

from typing import Any, Optional

DEFAULT_TONE = "gentle"
SUPPORTED_TONES = ("gentle", "direct", "clinical")

# Lead-ins prepended to a recommendation's action line, by tone and by
# the recommendation's own (unmodified) priority.
_ACTION_LEAD_IN: dict[str, dict[str, str]] = {
    "gentle": {
        "HIGH": "When you're ready, the highest-leverage change is:",
        "MEDIUM": "Worth trying this week:",
        "LOW": "A small optional tweak:",
    },
    "direct": {
        "HIGH": "Start here. This is the one that matters most:",
        "MEDIUM": "Do this next:",
        "LOW": "Minor, but it helps:",
    },
    "clinical": {
        "HIGH": "Highest-impact intervention indicated:",
        "MEDIUM": "Secondary intervention:",
        "LOW": "Low-impact adjustment:",
    },
}

# How the overall result is framed, by tone and score band, in every
# language the app ships.
#
# This is the first line a user reads on their result screen, and it was
# English-only in all four - the one sentence that opens the whole
# result, in a language a Persian or Arabic reader may not read at all.
# The three tones are kept genuinely distinct in each language rather
# than translated once and reused: "direct" that reads as gentle in
# Persian is not the tone the user chose.
LANGUAGES = ("en", "fa", "ar", "zh")

_RESULT_FRAMING: dict[str, dict[str, dict[str, str]]] = {
    "gentle": {
        "great": {
            "en": "This is a genuinely good result — whatever you're doing, it's working.",
            "fa": "این واقعاً نتیجه‌ی خوبی است — هر کاری می‌کنی، دارد جواب می‌دهد.",
            "ar": "هذه نتيجة جيدة فعلاً — ما تفعله ناجح، فاستمر عليه.",
            "zh": "这是一个真正不错的结果——你目前的做法很有效。",
        },
        "good": {
            "en": "You're in a solid place. Small adjustments will keep you there.",
            "fa": "جایگاه محکمی داری. تنظیم‌های کوچک همین‌جا نگهت می‌دارد.",
            "ar": "أنت في وضع متين. تعديلات صغيرة تكفي للبقاء عليه.",
            "zh": "你的状态很稳。小幅调整就能保持下去。",
        },
        "borderline": {
            "en": "You're right on the edge. A little attention now goes a long way.",
            "fa": "دقیقاً روی مرز هستی. کمی توجه از همین حالا خیلی فرق می‌کند.",
            "ar": "أنت عند الحد تماماً. قليل من الانتباه الآن يُحدث فرقاً كبيراً.",
            "zh": "你正好处在临界点。现在稍加留意，效果会很明显。",
        },
        "risk": {
            "en": "This one's low, and it's worth taking seriously — but every factor behind it is changeable.",
            "fa": "این عدد پایین است و جدی گرفتنش می‌ارزد — اما هر عاملی که پشتش هست قابل تغییر است.",
            "ar": "هذه النتيجة منخفضة وتستحق أن تؤخذ بجدية — لكن كل عامل وراءها قابل للتغيير.",
            "zh": "这个分数偏低，值得认真对待——但背后的每一项因素都是可以改变的。",
        },
    },
    "direct": {
        "great": {
            "en": "Strong result. Keep the pattern.",
            "fa": "نتیجه‌ی قوی. همین الگو را حفظ کن.",
            "ar": "نتيجة قوية. حافظ على هذا النمط.",
            "zh": "结果很好。保持这个模式。",
        },
        "good": {
            "en": "Decent. Not much to fix, but don't drift.",
            "fa": "قابل قبول. چیز زیادی برای اصلاح نیست، ولی رها نکن.",
            "ar": "مقبولة. لا يوجد الكثير لإصلاحه، لكن لا تتراخَ.",
            "zh": "还行。没什么要修的，但别松懈。",
        },
        "borderline": {
            "en": "Borderline. Act before this slides.",
            "fa": "مرزی. قبل از اینکه سُر بخورد اقدام کن.",
            "ar": "على الحد. تحرّك قبل أن تتراجع.",
            "zh": "处于临界。在下滑之前就该行动。",
        },
        "risk": {
            "en": "This is a low score. The good news: the main drivers are all things you control.",
            "fa": "این امتیاز پایینی است. خبر خوب: عامل‌های اصلی‌اش همه در کنترل خودت هستند.",
            "ar": "هذه درجة منخفضة. والخبر الجيد أن محرّكاتها الأساسية كلها تحت سيطرتك.",
            "zh": "这是个低分。好消息是：主要成因都在你的掌控之内。",
        },
    },
    "clinical": {
        "great": {
            "en": "Score falls in the upper band. Current pattern is favourable.",
            "fa": "امتیاز در باند بالایی قرار می‌گیرد. الگوی فعلی مطلوب است.",
            "ar": "تقع الدرجة في النطاق الأعلى. النمط الحالي مواتٍ.",
            "zh": "分数落在高区间。当前模式良好。",
        },
        "good": {
            "en": "Score falls in the healthy band with minor deviations.",
            "fa": "امتیاز با انحراف‌های جزئی در باند سالم قرار می‌گیرد.",
            "ar": "تقع الدرجة في النطاق الصحي مع انحرافات طفيفة.",
            "zh": "分数落在健康区间，存在轻微偏差。",
        },
        "borderline": {
            "en": "Score falls near the classification boundary.",
            "fa": "امتیاز نزدیک مرز طبقه‌بندی قرار می‌گیرد.",
            "ar": "تقع الدرجة قرب حدّ التصنيف.",
            "zh": "分数接近分类边界。",
        },
        "risk": {
            "en": "Score falls in the lower band. Primary contributing factors are modifiable.",
            "fa": "امتیاز در باند پایینی قرار می‌گیرد. عوامل اصلی مؤثر قابل تغییر هستند.",
            "ar": "تقع الدرجة في النطاق الأدنى. العوامل المساهمة الأساسية قابلة للتعديل.",
            "zh": "分数落在低区间。主要影响因素均可调整。",
        },
    },
}


def normalize_tone(tone: Optional[str]) -> str:
    """Unknown/absent tone falls back to the documented default rather
    than raising - a bad stored preference should never block advice."""
    return tone if tone in SUPPORTED_TONES else DEFAULT_TONE


def band_for_score(score: Optional[float]) -> str:
    """Same thresholds the result ring and mascot already use - not a
    second opinion about what counts as a good score."""
    if score is None:
        return "borderline"
    if score >= 80:
        return "great"
    if score >= 66:
        return "good"
    if score >= 40:
        return "borderline"
    return "risk"


def frame_result(score: Optional[float], tone: Optional[str] = None) -> str:
    """The English framing. Kept as-is so every existing caller and any
    older client reading `result_framing` is unaffected."""
    return _RESULT_FRAMING[normalize_tone(tone)][band_for_score(score)]["en"]


def frame_result_i18n(score: Optional[float], tone: Optional[str] = None) -> dict[str, str]:
    """The same framing in every shipped language, keyed by language code.

    Returned alongside the English string rather than instead of it: the
    server does not know which language the reader has selected (that
    lives in the browser), so it sends all four and the UI picks one -
    the same arrangement `RecommendationResponse.text_i18n` already uses
    for recommendation text.
    """
    return dict(_RESULT_FRAMING[normalize_tone(tone)][band_for_score(score)])


def lead_in_for(priority: str, tone: Optional[str] = None) -> str:
    table = _ACTION_LEAD_IN[normalize_tone(tone)]
    return table.get((priority or "").upper(), table["MEDIUM"])


def apply_tone(recommendations: list[Any], tone: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Return each recommendation as a plain dict with one ADDED field,
    `action_lead_in`. The original title/description/action/priority/
    success_metric/safety_note are copied verbatim - this function
    deliberately cannot alter them, so a tone preference can never
    change what the user is actually being advised to do.
    """
    resolved = normalize_tone(tone)
    out: list[dict[str, Any]] = []
    for rec in recommendations:
        data = rec.to_dict() if hasattr(rec, "to_dict") else dict(rec)
        data["action_lead_in"] = lead_in_for(data.get("priority", "MEDIUM"), resolved)
        out.append(data)
    return out
