"""
services/report_i18n.py
-----------------------
Fonts, text shaping and strings for the four-language PDF report
(C-5-9) and the four-language CSV export (C-5-7).

Three separate problems get solved here, and it is worth being precise
about which is which, because "the PDF is in Persian" quietly means all
three:

  1. Glyphs. reportlab's built-in Helvetica has no Arabic and no CJK
     coverage at all, so Persian text renders as empty boxes. DejaVu
     Sans (present on essentially every Linux image, and checked for at
     import time) covers Latin, Arabic and Arabic Presentation Forms-B.
     Chinese uses reportlab's own STSong-Light CID font, which ships
     with the library - no font file to bundle.

  2. Shaping and direction. reportlab draws the code points it is
     given, left to right, with no complex-script shaping: Arabic
     letters come out isolated and in the wrong order. arabic_reshaper
     converts the logical string into presentation forms and python-bidi
     reorders it visually. That work has to happen before the string
     reaches reportlab, which is what `shape()` is for.

  3. Words. A report in a language whose headings are still English is
     not translated; STRINGS below carries every piece of report and CSV
     chrome in all four.

If the shaping libraries or the font are unavailable, the report still
generates - in English, with a note explaining why - rather than
failing or, worse, emitting a page of empty boxes that looks like a
rendering bug. `report_language_support()` reports exactly what is
available so a caller can tell the user the truth.
"""

from __future__ import annotations

import os
from typing import Any

RTL_LANGUAGES = {"fa", "ar"}
SUPPORTED_LANGUAGES = ("en", "fa", "ar", "zh")

# Font files searched in order. The first that exists wins.
_LATIN_ARABIC_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/Library/Fonts/DejaVuSans.ttf",
    "C:\\Windows\\Fonts\\DejaVuSans.ttf",
)
_LATIN_ARABIC_BOLD_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
)

FONT_REGULAR = "DWSans"
FONT_BOLD = "DWSans-Bold"
FONT_CJK = "STSong-Light"

_registered: dict[str, bool] = {}


def _first_existing(paths: tuple[str, ...]) -> str | None:
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def register_fonts() -> dict[str, bool]:
    """Registers what is available. Idempotent; safe to call per report."""
    if _registered:
        return _registered

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular = _first_existing(_LATIN_ARABIC_CANDIDATES)
    bold = _first_existing(_LATIN_ARABIC_BOLD_CANDIDATES)
    _registered["unicode"] = False
    _registered["cjk"] = False

    if regular:
        try:
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, regular))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, bold or regular))
            from reportlab.lib.fonts import addMapping
            addMapping(FONT_REGULAR, 0, 0, FONT_REGULAR)
            addMapping(FONT_REGULAR, 1, 0, FONT_BOLD)
            addMapping(FONT_REGULAR, 0, 1, FONT_REGULAR)
            addMapping(FONT_REGULAR, 1, 1, FONT_BOLD)
            _registered["unicode"] = True
        except Exception:  # noqa: BLE001 - a broken font file must not stop the report
            _registered["unicode"] = False

    try:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont(FONT_CJK))
        _registered["cjk"] = True
    except Exception:  # noqa: BLE001
        _registered["cjk"] = False

    return _registered


def _shaping_available() -> bool:
    try:
        import arabic_reshaper  # noqa: F401
        from bidi.algorithm import get_display  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def report_language_support(lang: str) -> dict[str, Any]:
    """What can actually be rendered for `lang` right now.

    Callers use this to decide whether to fall back rather than
    discovering the problem as a page of empty rectangles.
    """
    fonts = register_fonts()
    lang = normalise(lang)
    if lang == "zh":
        ok = fonts.get("cjk", False)
        reason = "" if ok else "no CJK font available"
    elif lang in RTL_LANGUAGES:
        ok = fonts.get("unicode", False) and _shaping_available()
        if ok:
            reason = ""
        elif not fonts.get("unicode", False):
            reason = "no Unicode font with Arabic coverage available"
        else:
            reason = "arabic-reshaper / python-bidi not installed"
    else:
        ok = True
        reason = ""
    return {"language": lang, "supported": ok, "reason": reason}


def normalise(lang: str | None) -> str:
    lang = (lang or "en").lower().split("-")[0]
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def font_for(lang: str) -> str:
    lang = normalise(lang)
    fonts = register_fonts()
    if lang == "zh" and fonts.get("cjk"):
        return FONT_CJK
    if fonts.get("unicode"):
        return FONT_REGULAR
    return "Helvetica"


def bold_font_for(lang: str) -> str:
    lang = normalise(lang)
    fonts = register_fonts()
    if lang == "zh" and fonts.get("cjk"):
        return FONT_CJK  # the CID font has no separate bold face
    if fonts.get("unicode"):
        return FONT_BOLD
    return "Helvetica-Bold"


def is_rtl(lang: str) -> bool:
    return normalise(lang) in RTL_LANGUAGES


def shape(value: Any, lang: str) -> str:
    """Logical text in, drawable text out.

    A no-op for everything except Persian and Arabic, where the string
    is converted to presentation forms and reordered visually. Called on
    every string that reaches reportlab - including numbers, which is
    harmless, and including strings that are already English, which the
    bidi algorithm leaves alone.
    """
    text = "" if value is None else str(value)
    if not text or not is_rtl(lang):
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:  # noqa: BLE001 - unshaped text beats no report
        return text


def wrap_rtl(text: Any, font_name: str, font_size: float, max_width: float) -> list[str]:
    """Line-break FIRST, then shape each line. Returns drawable lines.

    This ordering is the whole point. reportlab wraps a paragraph after
    it receives the string, so shaping the entire paragraph up front and
    handing it over produces a page whose lines are in reverse order -
    the last line of the sentence printed first. It looks like the text
    was scrambled, and it is what a naive reshape+bidi+Paragraph always
    does. Breaking the logical text into lines that fit, and only then
    reordering each line for display, keeps the lines in reading order
    and each line correct within itself.
    """
    from reportlab.pdfbase.pdfmetrics import stringWidth

    words = str(text or "").split()
    if not words:
        return []

    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = current + [word]
        rendered = shape(" ".join(candidate), "fa")
        if current and stringWidth(rendered, font_name, font_size) > max_width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current = candidate
    if current:
        lines.append(" ".join(current))
    return [shape(line, "fa") for line in lines]


# --------------------------------------------------------------------
# Report and export strings
# --------------------------------------------------------------------

STRINGS: dict[str, dict[str, str]] = {
    "report_title": {
        "en": "Digital Wellness Report",
        "fa": "گزارش سلامت دیجیتال",
        "ar": "تقرير العافية الرقمية",
        "zh": "数字健康报告",
    },
    "generated": {"en": "Generated", "fa": "تاریخ تولید", "ar": "تاريخ الإنشاء", "zh": "生成时间"},
    "summary_heading": {
        "en": "Prediction summary", "fa": "خلاصه‌ی پیش‌بینی",
        "ar": "ملخص التنبؤ", "zh": "预测摘要",
    },
    "status": {"en": "Status", "fa": "وضعیت", "ar": "الحالة", "zh": "状态"},
    "score_range": {
        "en": "Wellness score (likely range)", "fa": "امتیاز سلامت (بازه‌ی محتمل)",
        "ar": "درجة العافية (المدى المرجَّح)", "zh": "健康分数（可能区间）",
    },
    "point_estimate": {
        "en": "point estimate", "fa": "برآورد نقطه‌ای",
        "ar": "التقدير النقطي", "zh": "点估计",
    },
    "confidence": {"en": "Confidence", "fa": "اطمینان", "ar": "الثقة", "zh": "置信度"},
    "model": {"en": "Model", "fa": "مدل", "ar": "النموذج", "zh": "模型"},
    "not_available": {"en": "Not available", "fa": "در دسترس نیست", "ar": "غير متاح", "zh": "不可用"},
    "inputs_heading": {
        "en": "Your inputs for this day", "fa": "ورودی‌های تو برای این روز",
        "ar": "مدخلاتك لهذا اليوم", "zh": "你这一天的输入",
    },
    "signals_heading": {
        "en": "What moved the score", "fa": "چه چیزی امتیاز را جابه‌جا کرد",
        "ar": "ما الذي حرّك الدرجة", "zh": "是什么改变了分数",
    },
    "signal": {"en": "Signal", "fa": "سیگنال", "ar": "الإشارة", "zh": "信号"},
    "effect": {"en": "Effect on the score", "fa": "اثر روی امتیاز", "ar": "الأثر على الدرجة", "zh": "对分数的影响"},
    "raises": {"en": "raises", "fa": "بالا می‌برد", "ar": "يرفع", "zh": "提高"},
    "lowers": {"en": "lowers", "fa": "پایین می‌آورد", "ar": "يخفض", "zh": "降低"},
    "recs_heading": {
        "en": "Personalized recommendations", "fa": "توصیه‌های شخصی‌سازی‌شده",
        "ar": "توصيات مخصَّصة", "zh": "个性化建议",
    },
    "priority": {"en": "priority", "fa": "اولویت", "ar": "الأولوية", "zh": "优先级"},
    "action": {"en": "Action", "fa": "اقدام", "ar": "الإجراء", "zh": "行动"},
    "success_metric": {
        "en": "How you will know it worked", "fa": "از کجا می‌فهمی جواب داده",
        "ar": "كيف ستعرف أنه نجح", "zh": "你怎么知道它起作用了",
    },
    "about_heading": {
        "en": "About this report", "fa": "درباره‌ی این گزارش",
        "ar": "حول هذا التقرير", "zh": "关于这份报告",
    },
    "synthetic_note": {
        "en": ("This model was trained on a synthetically generated dataset, not on data "
               "collected from real people. The score and explanations above are computed "
               "from your own real answers, but the patterns the model learned come from "
               "simulated diaries. Treat this as a research demo, not a measurement of "
               "your health, and not medical advice."),
        "fa": ("این مدل روی مجموعه‌داده‌ای که به‌صورت مصنوعی تولید شده آموزش دیده، نه روی داده‌ای "
               "که از افراد واقعی جمع‌آوری شده باشد. امتیاز و توضیحات بالا از پاسخ‌های واقعی خودت "
               "حساب شده‌اند، اما الگوهایی که مدل یاد گرفته از دفترچه‌های شبیه‌سازی‌شده می‌آیند. "
               "این را یک نمونه‌ی پژوهشی بدان، نه اندازه‌گیری سلامتت، و نه توصیه‌ی پزشکی."),
        "ar": ("دُرِّب هذا النموذج على مجموعة بيانات مولَّدة اصطناعياً، لا على بيانات جُمعت من أشخاص "
               "حقيقيين. الدرجة والتفسيرات أعلاه محسوبة من إجاباتك الحقيقية أنت، لكن الأنماط التي "
               "تعلّمها النموذج تأتي من يوميات محاكاة. اعتبر هذا عرضاً بحثياً، لا قياساً لصحتك، "
               "وليس نصيحة طبية."),
        "zh": ("该模型是在合成生成的数据集上训练的，而不是在从真实的人那里收集的数据上。上面的分数和解释"
               "是根据你自己真实的回答计算出来的，但模型学到的模式来自模拟的日记。请把它当作一个研究演示，"
               "而不是对你健康状况的测量，也不是医疗建议。"),
    },
    "range_note": {
        "en": ("The score is reported as a range because the model has a known average error, "
               "measured on a validation split it was not trained on."),
        "fa": ("امتیاز به‌صورت یک بازه گزارش می‌شود، چون مدل خطای میانگین مشخصی دارد که روی بخش "
               "اعتبارسنجی — که روی آن آموزش ندیده — اندازه‌گیری شده است."),
        "ar": ("تُعرض الدرجة كمدى لأن للنموذج خطأً متوسطاً معروفاً، مقيساً على شريحة تحقق لم يُدرَّب عليها."),
        "zh": "分数以区间形式给出，因为该模型有一个已知的平均误差，是在它未参与训练的验证集上测得的。",
    },
    "footer": {
        "en": "Generated by Digital Wellness AI",
        "fa": "تولیدشده توسط Digital Wellness AI",
        "ar": "أُنشئ بواسطة Digital Wellness AI",
        "zh": "由 Digital Wellness AI 生成",
    },
    "fallback_note": {
        "en": ("This report was generated in English: the server does not currently have the "
               "font or text-shaping support needed to typeset your language correctly, and "
               "an unreadable report would be worse than an English one."),
        "fa": ("این گزارش به انگلیسی تولید شد: سرور در حال حاضر فونت یا پشتیبانی شکل‌دهی متن لازم "
               "برای حروف‌چینی درست زبان تو را ندارد، و گزارش ناخوانا از گزارش انگلیسی بدتر است."),
        "ar": ("أُنشئ هذا التقرير بالإنجليزية: لا يملك الخادم حالياً الخط أو دعم تشكيل النص اللازم "
               "لتنضيد لغتك بشكل صحيح، وتقرير غير مقروء أسوأ من تقرير بالإنجليزية."),
        "zh": ("这份报告以英文生成：服务器目前没有正确排版你的语言所需的字体或文字整形支持，"
               "而一份读不了的报告比一份英文报告更糟。"),
    },
    # CSV export chrome (C-5-7)
    "csv_date": {"en": "Date", "fa": "تاریخ", "ar": "التاريخ", "zh": "日期"},
    "csv_day": {"en": "Day of week", "fa": "روز هفته", "ar": "يوم الأسبوع", "zh": "星期"},
    "csv_score": {"en": "Wellness score", "fa": "امتیاز سلامت", "ar": "درجة العافية", "zh": "健康分数"},
    "csv_class": {"en": "Status", "fa": "وضعیت", "ar": "الحالة", "zh": "状态"},
    "csv_excluded": {"en": "Marked as exception", "fa": "علامت‌خورده به‌عنوان استثنا", "ar": "مُعلَّم كاستثناء", "zh": "标记为例外"},
    "csv_yes": {"en": "yes", "fa": "بله", "ar": "نعم", "zh": "是"},
    "csv_no": {"en": "no", "fa": "خیر", "ar": "لا", "zh": "否"},
}

# Human-readable field labels, shared by the PDF's input table and the
# CSV header row so the two never disagree.
FIELD_LABELS: dict[str, dict[str, str]] = {
    "total_screen_min": {"en": "Total screen time (min)", "fa": "زمان کل صفحه (دقیقه)", "ar": "إجمالي وقت الشاشة (دقيقة)", "zh": "总屏幕时间（分钟）"},
    "social_min": {"en": "Social apps (min)", "fa": "شبکه‌های اجتماعی (دقیقه)", "ar": "تطبيقات التواصل (دقيقة)", "zh": "社交应用（分钟）"},
    "gaming_min": {"en": "Gaming (min)", "fa": "بازی (دقیقه)", "ar": "الألعاب (دقيقة)", "zh": "游戏（分钟）"},
    "work_study_min": {"en": "Work / study (min)", "fa": "کار یا درس (دقیقه)", "ar": "العمل أو الدراسة (دقيقة)", "zh": "工作/学习（分钟）"},
    "video_min": {"en": "Video (min)", "fa": "ویدیو (دقیقه)", "ar": "الفيديو (دقيقة)", "zh": "视频（分钟）"},
    "sleep_hours": {"en": "Sleep (hours)", "fa": "خواب (ساعت)", "ar": "النوم (ساعات)", "zh": "睡眠（小时）"},
    "sleep_quality_1_10": {"en": "Sleep quality (1-10)", "fa": "کیفیت خواب (۱ تا ۱۰)", "ar": "جودة النوم (1-10)", "zh": "睡眠质量（1-10）"},
    "stress_0_10": {"en": "Stress (0-10)", "fa": "استرس (۰ تا ۱۰)", "ar": "التوتر (0-10)", "zh": "压力（0-10）"},
    "focus_0_100": {"en": "Focus (0-100)", "fa": "تمرکز (۰ تا ۱۰۰)", "ar": "التركيز (0-100)", "zh": "专注度（0-100）"},
    "productivity_0_100": {"en": "Productivity (0-100)", "fa": "بهره‌وری (۰ تا ۱۰۰)", "ar": "الإنتاجية (0-100)", "zh": "效率（0-100）"},
    "physical_activity_min_per_day": {"en": "Physical activity (min)", "fa": "فعالیت بدنی (دقیقه)", "ar": "النشاط البدني (دقيقة)", "zh": "身体活动（分钟）"},
    "night_screen_min": {"en": "Late-night screen time (min)", "fa": "زمان صفحه در شب (دقیقه)", "ar": "وقت الشاشة ليلاً (دقيقة)", "zh": "深夜屏幕时间（分钟）"},
    "pre_sleep_screen_min": {"en": "Screen time before sleep (min)", "fa": "زمان صفحه پیش از خواب (دقیقه)", "ar": "وقت الشاشة قبل النوم (دقيقة)", "zh": "睡前屏幕时间（分钟）"},
    "night_ratio": {"en": "Share of use at night", "fa": "سهم استفاده در شب", "ar": "حصة الاستخدام ليلاً", "zh": "夜间使用占比"},
    "social_ratio": {"en": "Share of use on social", "fa": "سهم استفاده در شبکه‌های اجتماعی", "ar": "حصة الاستخدام في التواصل", "zh": "社交使用占比"},
    "work_study_ratio": {"en": "Share of use on work / study", "fa": "سهم استفاده برای کار یا درس", "ar": "حصة الاستخدام للعمل أو الدراسة", "zh": "工作/学习使用占比"},
    "gaming_ratio": {"en": "Share of use on gaming", "fa": "سهم استفاده در بازی", "ar": "حصة الاستخدام في الألعاب", "zh": "游戏使用占比"},
    "fragmentation_index_0_100": {"en": "Fragmentation (0-100)", "fa": "تکه‌تکه‌شدگی (۰ تا ۱۰۰)", "ar": "التجزؤ (0-100)", "zh": "碎片化（0-100）"},
    "pickups_per_day": {"en": "Phone pickups", "fa": "دفعات برداشتن گوشی", "ar": "مرات التقاط الهاتف", "zh": "拿起手机次数"},
    "notification_density": {"en": "Notification density", "fa": "چگالی اعلان‌ها", "ar": "كثافة الإشعارات", "zh": "通知密度"},
    "social_comparison_1_10": {"en": "Online comparison (1-10)", "fa": "مقایسه‌ی آنلاین (۱ تا ۱۰)", "ar": "المقارنة على الإنترنت (1-10)", "zh": "网上比较（1-10）"},
    "health_score": {"en": "Wellness score", "fa": "امتیاز سلامت", "ar": "درجة العافية", "zh": "健康分数"},
}


def t(key: str, lang: str) -> str:
    """A report string in `lang`, unshaped."""
    table = STRINGS.get(key)
    if not table:
        return key
    return table.get(normalise(lang)) or table["en"]


def field_label(field: str, lang: str) -> str:
    table = FIELD_LABELS.get(field)
    if table:
        return table.get(normalise(lang)) or table["en"]
    # An unmapped field is still readable rather than raw snake_case.
    return field.replace("_", " ").capitalize()
