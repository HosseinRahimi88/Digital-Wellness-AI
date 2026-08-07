"""
Minimal, headless stand-in for the `streamlit` package.
------------------------------------------------------------------
This sandbox has no network access, so the real `streamlit` PyPI
package cannot be installed. To still exercise every `app/pages/*.py`
module's *real, unmodified* top-level execution path (imports, widget
calls, session_state reads/writes, control flow) rather than skip UI
testing entirely, this stub implements just enough of the `st.*`
surface (enumerated by grepping every `st.xxx` call actually used
under `app/`) for each page to run start-to-finish without raising.

It does NOT render anything and does NOT verify pixel-level output -
it only proves the page's Python executes without an unhandled
exception, which is exactly what section 9 ("UI Test - pages open
without exception") of the polish request asks for. Real visual
verification still requires `streamlit run app/Home.py` with the real
package installed.

Design:
- Every widget function (`slider`, `number_input`, `selectbox`,
  `checkbox`, `button`, `form_submit_button`, ...) returns a sane
  default so a page's top-level code runs the same branch a real user
  would on first load. `set_widget_result()` lets a test force a
  specific widget (by its `key=`) to return a specific value - used to
  simulate "the user clicked Predict" / "the user submitted the form".
- `st.stop()` raises `_StopExecution`, a sentinel the test harness
  catches and treats as a *normal* page exit (this is exactly what a
  real Streamlit `st.stop()` does - halt this rerun, not a bug).
- `st.session_state` is a plain dict subclass supporting both
  `st.session_state["x"]` and `st.session_state.x` access, matching
  real Streamlit's SessionState API surface as used by this codebase.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any


class _StopExecution(Exception):
    """Raised by stop() - mirrors real Streamlit's st.stop() behavior."""


class SessionState(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, key, value):
        self[key] = value


session_state = SessionState()

# key -> forced return value, set per-test via set_widget_result()
_WIDGET_RESULTS: dict[str, Any] = {}


def set_widget_result(key: str, value: Any) -> None:
    _WIDGET_RESULTS[key] = value


def reset() -> None:
    session_state.clear()
    _WIDGET_RESULTS.clear()


# ----------------------------------------------------------------
# No-op layout / display calls
# ----------------------------------------------------------------
def _noop(*args, **kwargs):
    return None


set_page_config = _noop
title = _noop
subheader = _noop
header = _noop
write = _noop
markdown = _noop
caption = _noop
divider = _noop
success = _noop
info = _noop
warning = _noop
error = _noop
json = _noop
dataframe = _noop
image = _noop
progress = _noop
balloons = _noop
snow = _noop
plotly_chart = _noop


def metric(label=None, value=None, delta=None, help=None, **kwargs):
    return None


def stop():
    raise _StopExecution()


def rerun():
    # Real st.rerun() halts the current script run and restarts it -
    # for a one-shot page execution (as this harness does), halting is
    # the correct/only observable behavior, same as stop().
    raise _StopExecution()


def switch_page(path):
    return None


def download_button(*args, **kwargs):
    return False


# ----------------------------------------------------------------
# Widgets - return the explicit `value=` default (matching how a real
# first page-load behaves), unless overridden via set_widget_result().
# ----------------------------------------------------------------
def _widget(key=None, default=None):
    if key is not None and key in _WIDGET_RESULTS:
        return _WIDGET_RESULTS[key]
    return default


def button(label, key=None, **kwargs):
    # Several buttons in this app (e.g. the "Predict" submit button) are
    # never given an explicit `key=`; fall back to the label so tests
    # can still target them via set_widget_result(label, True).
    return _widget(key or label, default=False)


def form_submit_button(label="Submit", key=None, **kwargs):
    return _widget(key or label, default=False)


def checkbox(label, value=False, key=None, **kwargs):
    return _widget(key, default=value)


def slider(label, min_value=None, max_value=None, value=None, step=None, key=None, **kwargs):
    return _widget(key, default=value)


def number_input(label, min_value=None, max_value=None, value=None, step=None, key=None, **kwargs):
    return _widget(key, default=value)


def selectbox(label, options, index=0, key=None, **kwargs):
    default = options[index] if options else None
    return _widget(key, default=default)


def radio(label, options, index=0, key=None, **kwargs):
    default = options[index] if options else None
    return _widget(key, default=default)


def text_input(label, value="", key=None, **kwargs):
    return _widget(key, default=value)


def text_area(label, value="", key=None, **kwargs):
    return _widget(key, default=value)


# ----------------------------------------------------------------
# Context managers
# ----------------------------------------------------------------
class _Column:
    """Real st.columns()/st.tabs()/st.expander() return objects that
    also support most top-level st.* calls as methods (e.g.
    `col.write(...)`, `col.metric(...)`) - proxy those through."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __getattr__(self, name):
        value = globals().get(name)
        if callable(value):
            return value
        raise AttributeError(name)


def columns(spec, **kwargs):
    n = spec if isinstance(spec, int) else len(spec)
    return [_Column() for _ in range(n)]


def tabs(labels):
    return [_Column() for _ in labels]


@contextmanager
def expander(label, **kwargs):
    yield _Column()


@contextmanager
def spinner(text=None):
    yield


@contextmanager
def form(key, **kwargs):
    yield _Column()


# ----------------------------------------------------------------
# Caching decorators - just call straight through (no actual caching
# needed for a single headless run per test).
# ----------------------------------------------------------------
def cache_resource(func=None, **kwargs):
    if func is not None:
        return func

    def wrapper(f):
        return f

    return wrapper


def cache_data(func=None, **kwargs):
    if func is not None:
        return func

    def wrapper(f):
        return f

    return wrapper


# ----------------------------------------------------------------
# Additions for the Group A product/UX features (score battery,
# sparklines, text-to-speech, animated guide, future letter, ...).
# Same "no-op / sane default" philosophy as the rest of this stub.
# ----------------------------------------------------------------
audio = _noop


def container(*args, **kwargs):
    return _Column()


@contextmanager
def empty():
    yield _Column()


def date_input(label, value=None, key=None, **kwargs):
    return _widget(key, default=value)


def toast(*args, **kwargs):
    return None


class _FakeComponentsV1:
    @staticmethod
    def html(html_code, height=None, width=None, scrolling=False, **kwargs):
        return None


class _FakeComponents:
    v1 = _FakeComponentsV1()


components = _FakeComponents()
