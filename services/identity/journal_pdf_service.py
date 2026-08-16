"""
Journal as a PDF
-----------------
The whole book, in one file the user can keep.

Why this is separate from services/identity/report_service.py: that report is
about the model's reading of a day - scores, factors, recommendations.
This one contains no scores at all. It is the user's own writing, and
mixing the two would put a number on a page whose entire point is that
it does not have one.

What it reuses instead is the typesetting: services/identity/report_i18n.py
already knows which font can draw Persian, Arabic and Chinese, how to
reshape and reorder right-to-left text before ReportLab draws it, and
how to wrap an RTL paragraph without printing its lines bottom-to-top.
Every one of those was found by rendering a real report and reading it,
and none of it is worth discovering twice.

Falling back
-------------
If the server cannot typeset the requested language, the book is
produced in that language's own text anyway where it can be, and the
page furniture falls back to English with a visible note - the same
rule the wellness report follows. A page of empty rectangles looks like
a broken app; a note explains itself.
"""

from __future__ import annotations

from datetime import date as date_cls, datetime
from io import BytesIO
from typing import Any, Iterable

from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from services.identity.report_i18n import (
    bold_font_for,
    font_for,
    is_rtl,
    normalise,
    report_language_support,
    shape,
    wrap_rtl,
)

# The book's own furniture, in the four languages the app speaks. Kept
# here rather than in report_i18n because nothing else prints them.
STRINGS: dict[str, dict[str, str]] = {
    "title": {
        "en": "The Book of Days",
        "fa": "کتابِ روزها",
        "ar": "كتاب الأيام",
        "zh": "日子之书",
    },
    "subtitle": {
        "en": "one page for every day you lived",
        "fa": "یک صفحه برای هر روزی که زیسته‌ای",
        "ar": "صفحة لكل يوم عشته",
        "zh": "你活过的每一天，都有一页",
    },
    "for": {"en": "Written by", "fa": "به قلمِ", "ar": "بقلم", "zh": "作者"},
    "pages": {"en": "pages", "fa": "صفحه", "ar": "صفحة", "zh": "页"},
    "span": {"en": "from {first} to {last}", "fa": "از {first} تا {last}",
             "ar": "من {first} إلى {last}", "zh": "自 {first} 至 {last}"},
    "exported": {"en": "Exported {when}", "fa": "خروجی‌گرفته در {when}",
                 "ar": "تم التصدير في {when}", "zh": "导出于 {when}"},
    "mood": {"en": "Mood", "fa": "حال", "ar": "المزاج", "zh": "心情"},
    "empty": {
        "en": "This book has no pages yet.",
        "fa": "این کتاب هنوز صفحه‌ای ندارد.",
        "ar": "لا يحتوي هذا الكتاب على صفحات بعد.",
        "zh": "这本书还没有任何一页。",
    },
    "notice": {
        "en": "This copy could not be typeset in the language you asked for, so its headings are in English. Your own writing is unchanged.",
        "fa": "این نسخه در زبانی که خواستی حروف‌چینی نشد، پس عنوان‌هایش انگلیسی است. نوشته‌ی خودت دست‌نخورده مانده.",
        "ar": "تعذّر تنضيد هذه النسخة باللغة التي طلبتها، لذا عناوينها بالإنجليزية. أما كتابتك فلم تتغيّر.",
        "zh": "这一份无法用你所选的语言排版，因此标题为英文。你自己写的内容未作改动。",
    },
    "note": {
        "en": "Nothing in this book was written by the app, and nothing in it was read by any model.",
        "fa": "هیچ‌چیز در این کتاب را اپ ننوشته، و هیچ مدلی آن را نخوانده است.",
        "ar": "لا شيء في هذا الكتاب كتبه التطبيق، ولم يقرأه أي نموذج.",
        "zh": "这本书里的内容都不是应用写的，也没有任何模型读过它。",
    },
}

MOODS: dict[str, dict[str, str]] = {
    "rough": {"en": "Rough", "fa": "سخت", "ar": "قاسٍ", "zh": "难熬"},
    "low": {"en": "Low", "fa": "پایین", "ar": "منخفض", "zh": "低落"},
    "steady": {"en": "Steady", "fa": "یکنواخت", "ar": "ثابت", "zh": "平稳"},
    "good": {"en": "Good", "fa": "خوب", "ar": "جيد", "zh": "不错"},
    "great": {"en": "Great", "fa": "عالی", "ar": "ممتاز", "zh": "很好"},
}

# Latin month names are used for every language, because the shipped
# fonts cover them and a locale-aware calendar (Jalali, Hijri) is a
# different feature with its own correctness questions. The ISO date is
# printed alongside, so no reader is left guessing.
_MONTHS = ("January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December")


def _t(key: str, lang: str) -> str:
    return STRINGS[key].get(lang) or STRINGS[key]["en"]


def _long_date(iso: str) -> str:
    try:
        day = date_cls.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso
    return f"{_MONTHS[day.month - 1]} {day.day}, {day.year}"


def _text_for(entry: dict, lang: str) -> str:
    """What this page says in this language.

    A demo page carries all four; a page a person typed carries the one
    they typed it in and is printed exactly as written, never machine
    translated into the language the PDF happens to be in.
    """
    bundle = entry.get("text_i18n") or {}
    return bundle.get(lang) or entry.get("text") or ""


def build(
    entries: Iterable[dict],
    lang: str = "en",
    display_name: str = "",
) -> BytesIO:
    """The whole book as a PDF, newest page first."""
    requested = normalise(lang)
    support = report_language_support(requested)
    language = requested if support["supported"] else "en"
    fell_back = language != requested

    rtl = is_rtl(language)
    body_font = font_for(language)
    heading_font = bold_font_for(language)
    align = TA_RIGHT if rtl else TA_LEFT

    rows = [e for e in (entries or []) if (e.get("text") or e.get("text_i18n"))]
    rows.sort(key=lambda e: e.get("date", ""), reverse=True)

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, title=_t("title", language), author=display_name or "",
    )
    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "JTitle", parent=base["Heading1"], fontName=heading_font,
        alignment=TA_CENTER, fontSize=22, leading=28,
        wordWrap="RTL" if rtl else None,
    )
    subtitle_style = ParagraphStyle(
        "JSub", parent=base["BodyText"], fontName=body_font,
        alignment=TA_CENTER, fontSize=10, textColor="#666666",
        wordWrap="RTL" if rtl else None,
    )
    date_style = ParagraphStyle(
        "JDate", parent=base["Heading2"], fontName=heading_font,
        alignment=align, fontSize=13, leading=18,
        wordWrap="RTL" if rtl else None,
    )
    body_style = ParagraphStyle(
        "JBody", parent=base["BodyText"], fontName=body_font,
        alignment=align, fontSize=11, leading=17,
        wordWrap="RTL" if rtl else None,
    )
    meta_style = ParagraphStyle(
        "JMeta", parent=base["BodyText"], fontName=body_font,
        alignment=align, fontSize=8.5, textColor="#888888",
        wordWrap="RTL" if rtl else None,
    )

    def para(value: Any, style: ParagraphStyle) -> Paragraph:
        """A paragraph that survives right-to-left wrapping.

        Same treatment as services/identity/report_service.py: for RTL the text
        is wrapped to the frame BEFORE being shaped, then joined with
        explicit breaks, because ReportLab wrapping an already-reordered
        string prints the lines of a sentence bottom to top.
        """
        text = "" if value is None else str(value)
        if not rtl:
            return Paragraph(shape(text, language), style)
        lines = wrap_rtl(text, style.fontName, style.fontSize, document.width * 0.96)
        fixed = ParagraphStyle(style.name + "-fixed", parent=style, wordWrap=None)
        return Paragraph("<br/>".join(lines) if lines else "", fixed)

    story: list = [
        para(_t("title", language), title_style),
        para(_t("subtitle", language), subtitle_style),
        Spacer(1, 10),
    ]
    if display_name:
        story.append(para(f'{_t("for", language)}: {display_name}', subtitle_style))
    if rows:
        story.append(para(
            f'{len(rows)} {_t("pages", language)} · '
            + _t("span", language)
            .replace("{first}", _long_date(rows[-1].get("date", "")))
            .replace("{last}", _long_date(rows[0].get("date", ""))),
            subtitle_style,
        ))
    story.append(para(
        _t("exported", language).replace(
            "{when}", datetime.now().strftime("%Y-%m-%d %H:%M")),
        subtitle_style,
    ))
    if fell_back:
        story.append(Spacer(1, 8))
        story.append(para(_t("notice", language), meta_style))
    story.append(Spacer(1, 6))
    story.append(para(_t("note", language), meta_style))
    story.append(Spacer(1, 16))

    if not rows:
        story.append(para(_t("empty", language), body_style))
    else:
        for index, entry in enumerate(rows):
            if index:
                story.append(Spacer(1, 14))
            story.append(para(_long_date(entry.get("date", "")), date_style))
            mood = entry.get("mood")
            if mood in MOODS:
                label = MOODS[mood].get(language) or MOODS[mood]["en"]
                story.append(para(f'{_t("mood", language)}: {label}', meta_style))
            story.append(Spacer(1, 4))
            for block in (_text_for(entry, language) or "").split("\n"):
                if block.strip():
                    story.append(para(block, body_style))
                else:
                    story.append(Spacer(1, 6))
            # A page break every eight entries, so a long book is a
            # readable document rather than one enormous column.
            if index and index % 8 == 7 and index != len(rows) - 1:
                story.append(PageBreak())

    document.build(story)
    buffer.seek(0)
    return buffer
