"""
Text-to-Speech Component
----------------------------
Reads a short piece of text aloud using the browser's built-in
`speechSynthesis` API - no external TTS service, no new Python
dependency, nothing sent over the network. Degrades silently (button
does nothing) on browsers without Web Speech API support, which is
acceptable for an optional accessibility nicety like this.
"""

from __future__ import annotations

import html
import json

import streamlit as st


class TextToSpeech:

    @staticmethod
    def render(text: str, label: str = "🔊 Listen", height: int = 46) -> None:
        if not text or not text.strip():
            return

        safe_text_json = json.dumps(text)
        safe_label = html.escape(label)

        widget_html = f"""
        <div>
          <button id="tts-btn" style="
              padding: 8px 14px; border-radius: 10px; border: 1px solid rgba(0,0,0,0.15);
              background: #f5f5f5; font-weight: 600; cursor: pointer; font-size: 14px;">
            {safe_label}
          </button>
          <span id="tts-status" style="margin-left:8px; font-size:12px; opacity:0.7;"></span>
        </div>
        <script>
          const ttsText = {safe_text_json};
          const btn = document.getElementById("tts-btn");
          const status = document.getElementById("tts-status");
          btn.addEventListener("click", function() {{
            if (!("speechSynthesis" in window)) {{
              status.textContent = "Not supported in this browser.";
              return;
            }}
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(ttsText);
            utterance.rate = 1.0;
            window.speechSynthesis.speak(utterance);
          }});
        </script>
        """
        st.components.v1.html(widget_html, height=height)
