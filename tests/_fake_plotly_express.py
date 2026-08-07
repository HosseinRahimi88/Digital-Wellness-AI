"""Minimal stand-in for `plotly.express` - see tests/_fake_streamlit.py
for why (no network access to pip install the real package). Every
chart-builder just needs to return *something* with `.update_traces` /
`.update_xaxes` / `.update_layout` chainable no-ops, since the pages
never inspect the returned figure - they only pass it to
`st.plotly_chart()`, which our fake streamlit also no-ops.
"""

from __future__ import annotations


class _FakeFigure:
    def update_traces(self, *a, **k):
        return self

    def update_xaxes(self, *a, **k):
        return self

    def update_yaxes(self, *a, **k):
        return self

    def update_layout(self, *a, **k):
        return self


def _make_figure(*args, **kwargs) -> _FakeFigure:
    return _FakeFigure()


pie = _make_figure
bar = _make_figure
line = _make_figure
scatter = _make_figure
imshow = _make_figure
