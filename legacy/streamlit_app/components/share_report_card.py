"""
Share Report Card Component
------------------------------
Generates a beautiful, downloadable PNG "report card" summarizing a
real prediction: Health Score, Health Class, Persona, a short summary,
and the date. Distinct from services/identity/report_service.py's full PDF
report - this is a compact, shareable image (like a social card).
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Optional

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

CARD_WIDTH = 1000
CARD_HEIGHT = 560

CLASS_COLORS = {
    "healthy": ("#2e7d32", "#e8f5e9"),
    "moderate": ("#ef6c00", "#fff3e0"),
    "at risk": ("#c62828", "#ffebee"),
}
DEFAULT_COLOR = ("#455a64", "#eceff1")

_FONT_CANDIDATES_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/Library/Fonts/Arial.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
]
_FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
]


def _load_font(size: int, bold: bool = False):
    candidates = _FONT_CANDIDATES_BOLD if bold else _FONT_CANDIDATES_REGULAR
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


class ShareReportCard:

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    @classmethod
    def generate_png(
        cls,
        health_score: Optional[float],
        health_class: str,
        persona: str,
        confidence: Optional[float],
        model_name: str,
        top_drivers: Optional[list[str]] = None,
        report_date: Optional[datetime] = None,
    ) -> BytesIO:
        report_date = report_date or datetime.now()
        accent_hex, bg_hex = CLASS_COLORS.get(str(health_class).strip().lower(), DEFAULT_COLOR)
        accent = cls._hex_to_rgb(accent_hex)
        bg = cls._hex_to_rgb(bg_hex)

        img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Background card with rounded corners
        margin = 24
        draw.rounded_rectangle(
            [margin, margin, CARD_WIDTH - margin, CARD_HEIGHT - margin],
            radius=28, fill=bg,
        )
        # Top accent bar
        draw.rounded_rectangle(
            [margin, margin, CARD_WIDTH - margin, margin + 90],
            radius=28, fill=accent,
        )
        draw.rectangle([margin, margin + 60, CARD_WIDTH - margin, margin + 90], fill=accent)

        font_title = _load_font(30, bold=True)
        font_score = _load_font(96, bold=True)
        font_label = _load_font(22, bold=True)
        font_body = _load_font(20)
        font_small = _load_font(16)

        # Note: emojis are intentionally avoided here (unlike elsewhere in
        # the app's Streamlit UI) because PIL's default fonts don't
        # reliably render color emoji glyphs into a static PNG.
        draw.text((60, margin + 22), "Digital Wellness Report", font=font_title, fill=(255, 255, 255))

        # Health score
        score_str = f"{health_score:.1f}" if health_score is not None else "N/A"
        draw.text((60, 170), score_str, font=font_score, fill=accent)
        draw.text((60, 275), "/ 100 Health Score", font=font_body, fill=(60, 60, 60))

        # Health class pill
        pill_text = str(health_class)
        pill_bbox = draw.textbbox((0, 0), pill_text, font=font_label)
        pill_w = (pill_bbox[2] - pill_bbox[0]) + 40
        pill_h = 46
        pill_x = 60
        pill_y = 320
        draw.rounded_rectangle(
            [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
            radius=pill_h // 2, fill=accent,
        )
        draw.text((pill_x + 20, pill_y + 10), pill_text, font=font_label, fill=(255, 255, 255))

        # Persona
        draw.text((60, 390), f"Persona: {persona}", font=font_body, fill=(40, 40, 40))

        # Confidence / model line
        conf_str = f"{confidence:.0%}" if confidence is not None else "N/A"
        draw.text((60, 425), f"Model confidence: {conf_str}  •  Model: {model_name}", font=font_small, fill=(90, 90, 90))

        # Top drivers
        if top_drivers:
            drivers_line = "Key factors: " + ", ".join(top_drivers[:3])
            draw.text((60, 455), drivers_line, font=font_small, fill=(90, 90, 90))

        # Date + footer
        draw.text((60, CARD_HEIGHT - 60), f"Generated {report_date:%B %d, %Y}", font=font_small, fill=(120, 120, 120))
        footer = "Digital Wellness AI"
        footer_bbox = draw.textbbox((0, 0), footer, font=font_small)
        footer_w = footer_bbox[2] - footer_bbox[0]
        draw.text((CARD_WIDTH - margin - 30 - footer_w, CARD_HEIGHT - 60), footer, font=font_small, fill=(120, 120, 120))

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    @classmethod
    def render(
        cls,
        prediction_result: Any,
        persona: str,
        title: str = "📤 Share Your Report",
    ) -> None:
        if title:
            st.subheader(title)

        shap_features = getattr(prediction_result, "shap_features", None) or []
        top_drivers = [getattr(f, "feature", "").replace("_", " ") for f in shap_features[:3] if getattr(f, "feature", None)]

        png_buffer = cls.generate_png(
            health_score=getattr(prediction_result, "regression_score", None),
            health_class=getattr(prediction_result, "prediction", "N/A"),
            persona=persona,
            confidence=getattr(prediction_result, "confidence", None),
            model_name=getattr(prediction_result, "model_name", ""),
            top_drivers=top_drivers,
        )

        png_bytes = png_buffer.getvalue()

        st.image(png_bytes, use_container_width=True)

        st.download_button(
            label="📥 Download Report Card (PNG)",
            data=png_bytes,
            file_name="digital_wellness_report_card.png",
            mime="image/png",
            use_container_width=True,
        )
