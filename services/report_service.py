"""
Report Service

Generates a downloadable PDF report for Digital Wellness AI, in the
user's own language (C-5-9).

Three things make this more than a string swap, and all three live in
services/report_i18n.py: reportlab's default fonts have no Arabic or
CJK glyphs, reportlab does no complex-script shaping so Persian and
Arabic need reshaping and bidi reordering before they are drawn, and
right-to-left languages need the whole page mirrored - alignment,
tables and all.

If the server cannot typeset the requested language, the report is
produced in English with a visible note saying why. A page of empty
rectangles would look like a bug in the app rather than a missing font.
"""

from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from config.report_settings import REPORT_HIGHLIGHT_FEATURES
from services.report_i18n import (
    bold_font_for,
    wrap_rtl,
    field_label,
    font_for,
    is_rtl,
    normalise,
    report_language_support,
    shape,
    t,
)


class ReportService:
    """
    Creates a downloadable PDF report.
    """

    def generate(
        self,
        user_data: dict,
        prediction_result,
        recommendations: list,
        lang: str = "en",
    ) -> BytesIO:
        requested = normalise(lang)
        support = report_language_support(requested)
        # Fall back rather than emit boxes; the reason is printed in the
        # report itself so the user is never left guessing.
        lang = requested if support["supported"] else "en"
        fell_back = lang != requested

        rtl = is_rtl(lang)
        body_font = font_for(lang)
        heading_font = bold_font_for(lang)
        align = TA_RIGHT if rtl else TA_LEFT

        def s(value) -> str:
            return shape(value, lang)

        def paragraph(value, style) -> Paragraph:
            """A paragraph that survives right-to-left wrapping.

            For LTR this is just Paragraph(text). For RTL the text is
            broken into lines that fit the frame BEFORE being shaped,
            and the lines are joined with explicit breaks - otherwise
            reportlab wraps the already-reordered string and prints the
            sentence's lines bottom-to-top. That bug is invisible in a
            one-line string and obvious in a paragraph, which is why it
            survived until the report was actually rendered and read.
            """
            text = "" if value is None else str(value)
            if not rtl:
                return Paragraph(text, style)
            # 0.96 of the frame, and wordWrap off on the clone: with RTL
            # wrapping still enabled reportlab re-wrapped the lines this
            # function had already measured, leaving one or two words
            # stranded on a line of their own.
            lines = wrap_rtl(text, style.fontName, style.fontSize, document.width * 0.96)
            fixed = ParagraphStyle(style.name + "-fixed", parent=style, wordWrap=None)
            return Paragraph("<br/>".join(lines) if lines else "", fixed)

        buffer = BytesIO()
        document = SimpleDocTemplate(buffer)
        base = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DWTitle", parent=base["Heading1"], fontName=heading_font,
            alignment=TA_CENTER, wordWrap="RTL" if rtl else None,
        )
        heading_style = ParagraphStyle(
            "DWHeading", parent=base["Heading2"], fontName=heading_font,
            alignment=align, wordWrap="RTL" if rtl else None,
        )
        body_style = ParagraphStyle(
            "DWBody", parent=base["BodyText"], fontName=body_font,
            alignment=align, wordWrap="RTL" if rtl else None, leading=15,
        )
        note_style = ParagraphStyle(
            "DWNote", parent=body_style, fontName=body_font, textColor=colors.HexColor("#555555"),
        )
        footer_style = ParagraphStyle(
            "DWFooter", parent=body_style, fontName=body_font, fontSize=8,
            textColor=colors.HexColor("#777777"),
        )

        def table_style(header_col=True) -> TableStyle:
            commands = [
                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 0), (-1, -1), body_font),
                # RTL tables read from the right: the label column has to
                # be the rightmost one, which is what reversing each row
                # plus right alignment achieves.
                ("ALIGN", (0, 0), (-1, -1), "RIGHT" if rtl else "LEFT"),
            ]
            if header_col:
                label_col = -1 if rtl else 0
                commands.append(("BACKGROUND", (label_col, 0), (label_col, -1), colors.lightgrey))
            return TableStyle(commands)

        def row(*cells) -> list:
            cells = [s(c) for c in cells]
            return list(reversed(cells)) if rtl else cells

        story = []
        story.append(Paragraph(s(t("report_title", lang)), title_style))
        story.append(Spacer(1, 20))
        story.append(Paragraph(
            s(f"{t('generated', lang)}: {datetime.now():%Y-%m-%d %H:%M}"), body_style))
        story.append(Spacer(1, 16))

        if fell_back:
            story.append(paragraph(t("fallback_note", requested), note_style))
            story.append(Spacer(1, 14))

        # ---- summary -------------------------------------------------
        story.append(Paragraph(s(t("summary_heading", lang)), heading_style))

        confidence_str = (
            f"{prediction_result.confidence:.1%}"
            if prediction_result.confidence is not None
            else t("not_available", lang)
        )

        # C-6-3: the wellness score belongs in the report, and as the
        # interval it actually is rather than a falsely precise number. The
        # bounds come from the same conformal service the UI shows, which
        # calibrates on the validation split - the test set is single-use
        # and is never involved. A report that quoted a bare number while
        # the screen showed a range would be the two disagreeing.
        uncertainty = getattr(prediction_result, "uncertainty", None)
        score = getattr(prediction_result, "regression_score", None)
        lower = getattr(uncertainty, "regression_lower", None) if uncertainty else None
        upper = getattr(uncertainty, "regression_upper", None) if uncertainty else None
        available = bool(getattr(uncertainty, "available", False)) if uncertainty else False

        if score is None:
            score_str = t("not_available", lang)
        elif available and lower is not None and upper is not None:
            score_str = f"{round(lower)}-{round(upper)} ({t('point_estimate', lang)} {score:.1f})"
        else:
            score_str = f"{score:.1f}"

        summary = [
            row(t("status", lang), prediction_result.prediction),
            row(t("score_range", lang), score_str),
            row(t("confidence", lang), confidence_str),
            row(t("model", lang), prediction_result.model_name),
        ]
        table = Table(summary)
        table.setStyle(table_style())
        story.append(table)
        story.append(Spacer(1, 20))

        # ---- the day's inputs ---------------------------------------
        story.append(Paragraph(s(t("inputs_heading", lang)), heading_style))
        rows = [
            row(field_label(feature, lang), user_data[feature])
            for feature in REPORT_HIGHLIGHT_FEATURES
            if feature in user_data
        ]
        if rows:
            table_stats = Table(rows)
            table_stats.setStyle(table_style())
            story.append(table_stats)
        story.append(Spacer(1, 20))

        # ---- what moved the score -----------------------------------
        # C-5-9 asked for a complete report; the SHAP explanation is the
        # single most important thing the app shows on screen and it was
        # simply missing from the PDF.
        shap_features = getattr(prediction_result, "shap_features", None) or []
        if shap_features:
            story.append(Paragraph(s(t("signals_heading", lang)), heading_style))
            shap_rows = [row(t("signal", lang), t("effect", lang))]
            for feature in shap_features:
                name = field_label(getattr(feature, "feature", ""), lang)
                impact = getattr(feature, "impact", None)
                if impact is None:
                    impact = getattr(feature, "shap_value", 0) or 0
                direction = t("raises", lang) if impact >= 0 else t("lowers", lang)
                shap_rows.append(row(name, f"{direction} ({abs(float(impact)):.2f})"))
            shap_table = Table(shap_rows)
            shap_table.setStyle(table_style(header_col=False))
            story.append(shap_table)
            story.append(Spacer(1, 20))

        # ---- recommendations ----------------------------------------
        story.append(Paragraph(s(t("recs_heading", lang)), heading_style))
        for rec in recommendations:
            # C-2/A-2: the rule text itself now travels in four
            # languages, so a Persian report no longer prints English
            # advice under Persian headings.
            i18n = getattr(rec, "text_i18n", None) or {}

            def part(name: str, fallback: str) -> str:
                table = i18n.get(name)
                if isinstance(table, dict):
                    return table.get(lang) or table.get("en") or fallback
                return fallback

            title = part("title", getattr(rec, "title", ""))
            priority = f"{getattr(rec, 'priority', '')} {t('priority', lang)}"
            # <b> tags are markup reportlab parses; after shaping they
            # would be reversed into unparseable text, so RTL gets the
            # plain title instead of a broken tag.
            lines = [f"{title} ({priority})" if rtl else f"<b>{title}</b> ({priority})"]
            description = part("description", getattr(rec, "description", ""))
            if description:
                lines.append(str(description))
            action = part("action", getattr(rec, "action", ""))
            if action:
                lines.append(f"{t('action', lang)}: {action}")
            # Included for the first time here: on screen every
            # recommendation states how the user will know it worked,
            # and a report that dropped it was quietly less useful.
            metric = part("success_metric", getattr(rec, "success_metric", "") or "")
            if metric:
                lines.append(f"{t('success_metric', lang)}: {metric}")
            if rtl:
                # Each field on its own paragraph: they are separate
                # sentences, and joining them would let one long line
                # wrap into the next field's text.
                for line in lines:
                    story.append(paragraph(line, body_style))
            else:
                story.append(Paragraph("<br/>".join(lines), body_style))
            story.append(Spacer(1, 8))

        story.append(Spacer(1, 20))

        # C-6-1/C-6-2: the same disclosure the app shows on screen. A report
        # is the artifact that gets forwarded and read out of context, so it
        # is the last place that should imply the model was trained on real
        # people or that its output is exact.
        story.append(Paragraph(s(t("about_heading", lang)), heading_style))
        story.append(paragraph(t("synthetic_note", lang), body_style))
        story.append(Spacer(1, 8))
        story.append(paragraph(t("range_note", lang), body_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph(s(t("footer", lang)), footer_style))

        document.build(story)
        buffer.seek(0)
        return buffer
