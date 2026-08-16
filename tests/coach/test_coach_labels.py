"""window.DWCoachLabels (frontend/assets/js/coach/coach-labels.js) - fixes the
bug found while auditing the AI Coach rewrite: coach-chat.js, ai-menu.js,
future-letter.js, insight-cards.js and games.js all read
`window.DWCoachLabels[fieldName]` expecting an already-localized label,
but the global was never defined anywhere, so every read silently fell
back to the raw snake_case field name in every language.

Two things are checked against the REAL files, not a re-implementation:
  1. The label table's keys match core/feature_schema.py's actual field
     names exactly - a schema field added or renamed should be caught
     here rather than silently falling back forever.
  2. The five original call sites plus app.js's own SHAP/recommendation
     label lookups (a second, English-only instance of the same gap -
     `state.featureSchemaMap[name].label` comes straight from
     core/feature_schema.py with no language variants) resolve through
     this table in a language other than English.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

REPO_ROOT = paths.PROJECT_ROOT
LABELS_JS = REPO_ROOT / "frontend" / "assets" / "js" / "coach/coach-labels.js"
SCHEMA_PY = REPO_ROOT / "core" / "feature_schema.py"


def _schema_field_names() -> set[str]:
    text = SCHEMA_PY.read_text(encoding="utf-8")
    return set(re.findall(r'name="([^"]*)"', text))


# Labels that are deliberately NOT schema input fields. The schema
# describes what the user submits; these are model outputs that are
# nonetheless stored per day and named out loud in the UI, so they need
# a four-language label for exactly the same reason the inputs do.
#
#   health_score - the wellness score. coach-history-family.js builds
#     "Is my {label} getting better or worse?" style questions over the
#     per-day stored fields, and the score is one of them; without an
#     entry here those questions read "health score" in Persian, Arabic
#     and Chinese. Mirrors services/identity/report_i18n.py FIELD_LABELS, which
#     carries the same entry for the same reason.
#
# Kept as an explicit allowlist rather than relaxing the check, so the
# original guard still holds: a label left behind after its schema field
# is renamed or removed is still a failure.
# Labels for things that are NOT model inputs but ARE shown to the user
# with a title, so they need the same four languages.
#   health_score              the model's own output, named all over the UI
#   sessions_per_day          asked in the check-in form to derive a field
#   first_check_after_waking_min   that the model does take
NON_SCHEMA_LABELS = {
    "health_score",
    "sessions_per_day",
    "first_check_after_waking_min",
    # The regressor's TARGET, not one of its inputs, which is why it is
    # absent from FEATURE_SCHEMA. It needs a label anyway: the cohort
    # table on the About page lists it beside the ten input signals, and
    # without one a Persian reader saw a row headed "health score 0 100"
    # in raw English - the fallback prints the field name.
    "health_score_0_100",
}


class TestCoachLabelsCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        cls.node = node
        script = (
            "globalThis.window = {};"
            "window.DWI18n = { get: () => 'en' };"
            f"require({json.dumps(str(LABELS_JS))});"
            "console.log(JSON.stringify(window.DWCoachLabels.__raw));"
        )
        result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise AssertionError("coach-labels.js failed to load: " + result.stderr)
        cls.raw = json.loads(result.stdout)

    def test_every_schema_field_has_a_label(self):
        missing = _schema_field_names() - set(self.raw)
        self.assertEqual(missing, set(), f"fields with no label entry: {sorted(missing)}")

    def test_no_stale_entries_for_fields_that_no_longer_exist(self):
        extra = set(self.raw) - _schema_field_names() - NON_SCHEMA_LABELS
        self.assertEqual(extra, set(), f"label entries for fields not in the schema: {sorted(extra)}")

    def test_the_non_schema_allowlist_is_not_itself_stale(self):
        # The allowlist above exists to permit specific labels, not to
        # accumulate. An entry named there but absent from the table
        # means the exemption outlived the thing it was exempting.
        absent = NON_SCHEMA_LABELS - set(self.raw)
        self.assertEqual(
            absent, set(),
            f"allowlisted labels that no longer exist in coach-labels.js: {sorted(absent)}",
        )

    def test_every_entry_has_all_four_languages_non_empty(self):
        offenders = {}
        for field, entry in self.raw.items():
            missing = [lang for lang in ("en", "fa", "ar", "zh") if not entry.get(lang)]
            if missing:
                offenders[field] = missing
        self.assertEqual(offenders, {}, f"entries missing a language: {offenders}")

    def test_resolves_through_the_proxy_in_the_current_language(self):
        script = (
            "globalThis.window = {};"
            "let lang = 'fa';"
            "window.DWI18n = { get: () => lang };"
            f"require({json.dumps(str(LABELS_JS))});"
            "const out = {};"
            "out.fa = window.DWCoachLabels['sleep_hours'];"
            "lang = 'zh'; out.zh = window.DWCoachLabels['sleep_hours'];"
            "lang = 'ar'; out.ar = window.DWCoachLabels['sleep_hours'];"
            "lang = 'xx'; out.fallback = window.DWCoachLabels['sleep_hours'];"  # unknown lang -> en
            "out.unknownField = window.DWCoachLabels['not_a_real_field'];"
            "console.log(JSON.stringify(out));"
        )
        result = subprocess.run([self.node, "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertNotEqual(out["fa"], "sleep_hours")
        self.assertNotEqual(out["zh"], "sleep_hours")
        self.assertNotEqual(out["ar"], "sleep_hours")
        self.assertEqual(out["fallback"], "Sleep duration")  # unknown UI language -> English, not undefined
        # JSON.stringify drops object keys whose value is `undefined`, so a
        # genuinely unknown field surfaces as an ABSENT key here, not null -
        # exactly what every caller's `|| fallback` already expects.
        self.assertNotIn("unknownField", out)


class TestAppJsUsesTheLabelRegistry(unittest.TestCase):
    """The main result page had the SAME gap through a different path -
    state.featureSchemaMap[name].label is real text but English only.
    These are static checks that app.js's SHAP/recommendation label
    lookups actually go through labelFor() (-> DWCoachLabels first) and
    not the raw English-only schema label directly."""

    @classmethod
    def setUpClass(cls):
        cls.app_js = (REPO_ROOT / "frontend" / "assets" / "js" / "pages/app.js").read_text(encoding="utf-8")

    def test_label_for_helper_exists_and_checks_coach_labels_first(self):
        self.assertIn("function labelFor(name)", self.app_js)
        idx = self.app_js.index("function labelFor(name)")
        body = self.app_js[idx:idx + 600]
        self.assertIn("window.DWCoachLabels", body)

    def test_no_call_site_reads_the_raw_english_only_schema_label_directly(self):
        # Every one of these used to read `(def && def.label) || ...`
        # directly. None should anymore - they should call labelFor().
        offending_patterns = [
            r"\(def\s*&&\s*def\.label\)",
            r"def\.label\)\s*\|\|",
        ]
        # Only the definition of labelFor() itself is allowed to contain
        # this pattern - it IS the fallback layer.
        helper_start = self.app_js.index("function labelFor(name)")
        helper_end = self.app_js.index("\n  }\n", helper_start)
        outside_helper = self.app_js[:helper_start] + self.app_js[helper_end:]
        for pattern in offending_patterns:
            matches = re.findall(pattern, outside_helper)
            self.assertEqual(matches, [], f"raw label fallback still present outside labelFor(): {pattern}")

    def test_coach_labels_script_loads_before_app_js_on_every_page_that_needs_it(self):
        for page in ("app.html", "dashboard.html", "coach.html", "analytics.html"):
            html = (REPO_ROOT / "frontend" / page).read_text(encoding="utf-8")
            with self.subTest(page=page):
                self.assertIn('src="assets/js/coach/coach-labels.js"', html)
                labels_pos = html.index('src="assets/js/coach/coach-labels.js"')
                i18n_pos = html.index('src="assets/js/core/i18n.js"')
                self.assertLess(i18n_pos, labels_pos, "coach-labels.js must load after i18n.js")


class TestDashboardCohortCardIsTranslated(unittest.TestCase):
    """P7 real-browser QA (fa) found dashboard.js's cohort comparison card
    completely bypassing i18n: "you: 140 | cohort avg: 219.1 (23th pct)"
    rendered in raw English on a Persian page, with the field name itself
    coming from row.field.replace(/_/g, ' ') instead of DWCoachLabels, and
    a broken "23th" ordinal on top of that. None of the other i18n
    scanners in tests/frontend/test_i18n_coverage.py catch this class of gap -
    there's no ternary and no if/else branch, just a plain template
    string with never any language check at all."""

    @classmethod
    def setUpClass(cls):
        cls.dashboard_js = (REPO_ROOT / "frontend" / "assets" / "js" / "pages/dashboard.js").read_text(encoding="utf-8")

    def test_cohort_row_and_empty_states_go_through_dwi18n(self):
        for key in ("dash_top_factor", "dash_no_recs", "dash_cohort_row", "dash_no_cohort_data"):
            self.assertIn(f"window.DWI18n.t('{key}')", self.dashboard_js)

    def test_no_raw_english_cohort_or_recommendation_strings_remain(self):
        offending = ["cohort avg:", "Not enough history yet to compare.",
                     "Run a check-in to get personalized recommendations here.",
                     "Top factor in your last result:"]
        for s in offending:
            self.assertNotIn(s, self.dashboard_js, f"raw English string still hardcoded: {s!r}")

    def test_cohort_field_name_goes_through_the_label_registry(self):
        idx = self.dashboard_js.index("cohortRows")
        block = self.dashboard_js[idx:idx + 1200]
        self.assertIn("window.DWCoachLabels", block)

    def test_the_broken_ordinal_suffix_is_gone(self):
        self.assertNotIn("'th pct'", self.dashboard_js)
        self.assertNotIn('"th pct"', self.dashboard_js)


if __name__ == "__main__":
    unittest.main()
