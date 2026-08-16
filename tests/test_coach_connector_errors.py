"""AI Coach connector error/fallback behaviour (P6).

Real bug found and fixed this round: the 50-question menu path
(coach.js's runMenuItem()) caught a failed connector request and showed
`Connector error: ${e.message}` - interpolating the RAW internal
ConnectorError message ("auth", "quota", "HTTP 500", a raw fetch
TypeError...) straight into an otherwise-translated sentence. The main
chat box (coach.js's send()) already routed the exact same error kinds
through connector-fit.js's describeError(), which gives a specific,
translated, actionable message per kind (auth/quota/network/timeout/
rate/provider) in all four languages. Two UI surfaces handling the same
errors inconsistently is exactly the kind of thing this suite exists to
pin down.

Runs the real frontend/assets/js/connector.js and connector-fit.js under
node (tests/js/connector_error_runner.js), same established pattern as
tests/test_games_eligibility.py and tests/test_coach_nlu_coverage.py.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve().parent / "js" / "connector_error_runner.js"

LANGS = ["en", "fa", "ar", "zh"]
KINDS = ["auth", "quota", "network", "timeout", "provider", "rate", "null"]


class TestConnectorErrorMessages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        result = subprocess.run(
            [node, str(RUNNER)],
            capture_output=True, text=True, timeout=30, cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            raise AssertionError("connector_error_runner.js failed: " + result.stderr)
        cls.report = json.loads(result.stdout)

    def test_every_language_and_kind_produced_a_message(self):
        for lang in LANGS:
            for kind in KINDS:
                msg = self.report[lang][kind]
                self.assertTrue(msg, f"{lang}/{kind} produced an empty message")

    def test_messages_are_not_the_raw_internal_kind_string(self):
        # The exact bug: seeing literally "auth" or "quota" (the raw
        # ConnectorError.message) instead of a real sentence would mean
        # describeError() was bypassed again.
        for lang in LANGS:
            for kind in ["auth", "quota", "network", "timeout"]:
                msg = self.report[lang][kind]
                self.assertNotEqual(msg.strip().lower(), kind)
                self.assertGreater(len(msg), len(kind) + 5)

    def test_auth_and_quota_never_leak_a_raw_http_status_or_provider_body(self):
        # readError() in connector.js gives AUTH/QUOTA a fixed message
        # specifically so nothing from the provider's response body can
        # be reflected into the UI. Confirm that guarantee holds all the
        # way through describeError() too.
        for lang in LANGS:
            for kind in ["auth", "quota"]:
                msg = self.report[lang][kind]
                self.assertNotIn("HTTP", msg)

    def test_provider_kind_gets_a_distinct_message_from_auth_and_quota(self):
        for lang in LANGS:
            provider_msg = self.report[lang]["provider"]
            self.assertNotEqual(provider_msg, self.report[lang]["auth"])
            self.assertNotEqual(provider_msg, self.report[lang]["quota"])

    def test_a_local_rate_limit_trip_is_distinguished_from_a_provider_quota_error(self):
        # describeError()'s one piece of real logic: a QUOTA-kind error
        # whose message starts with "rate:" is the app's OWN 20-per-minute
        # guard tripping, not the provider's billing - it should read as
        # "slow down" with the wait time, not "check your billing".
        for lang in LANGS:
            rate_msg = self.report[lang]["rate"]
            quota_msg = self.report[lang]["quota"]
            self.assertNotEqual(rate_msg, quota_msg)
            self.assertIn("37", rate_msg)

    def test_a_null_error_falls_back_to_the_generic_provider_message_not_a_crash(self):
        for lang in LANGS:
            self.assertEqual(self.report[lang]["null"], self.report[lang]["provider"])

    def test_all_four_languages_are_actually_distinct_translations(self):
        # Catches describeError() or its COPY table silently falling back
        # to English for ar/zh - the exact class of bug the rest of this
        # session's localization pass was about.
        for kind in KINDS:
            values = {lang: self.report[lang][kind] for lang in LANGS}
            self.assertEqual(
                len(set(values.values())), len(LANGS),
                f"kind={kind!r} has duplicate text across languages: {values}",
            )

    def test_coach_js_menu_item_path_routes_through_describe_error(self):
        # The actual regression pin for the bug this file documents.
        self.assertTrue(self.report["_static"]["usesDescribeError"])
        self.assertTrue(self.report["_static"]["noRawConnectorErrorTemplate"])


if __name__ == "__main__":
    unittest.main()
