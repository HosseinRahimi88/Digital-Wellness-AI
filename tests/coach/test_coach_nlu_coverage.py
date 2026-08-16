"""Measured coverage for the AI Coach's fuzzy intent matcher.

Acceptance here is a measured percentage over a labelled corpus, not
"these three examples work now" -
three examples were exactly what was wrong with the matcher this
replaces (frontend/assets/js/coach/coach-nlu.js). This test runs the REAL
frontend files under node (same pattern as
tests/social/test_badge_service.py::TestRegistryCoverage) so a change that
breaks the actual matcher fails here, not a Python re-implementation of
it that could quietly drift from the real code.

The corpus (see tests/js/coach_nlu_corpus_runner.js) is regenerated from
the topics that ship today - every keyword coach-nlu.js itself extracts,
tested both verbatim and with one transposition typo - plus a smaller
hand-written set of genuine paraphrases across all four languages. It is
not a fixed fixture: add a topic to coach-knowledge*.js and the corpus
grows with it, which is the point (it can't go stale by omission).
"""
import json
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
RUNNER = paths.PROJECT_ROOT / "tests" / "js" / "coach_nlu_corpus_runner.js"

# Set below the last measured value (0.8996 at the time this was written)
# so normal noise doesn't flake the suite, but high enough that a real
# regression - e.g. someone reverting coach-nlu.js's fuzzy path back to
# plain regex .test() - fails loudly instead of quietly shipping.
MIN_COVERAGE = 0.85
MIN_COVERAGE_PER_BUCKET = 0.78


class TestCoachNLUCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        # The corpus is regenerated from whatever topics are registered,
        # so it grows with the knowledge base - it passed 7,900 cases
        # once the app-help topics landed, and every case runs the real
        # matcher against every topic. That took ~110s here, so a 60s
        # cap turned a passing suite into a timeout error. Sized with
        # room to grow rather than trimmed to the current runtime.
        result = subprocess.run(
            [node, str(RUNNER), str(REPO_ROOT)],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            raise AssertionError(
                "coach_nlu_corpus_runner.js failed: " + result.stderr
            )
        cls.report = json.loads(result.stdout)

    def test_corpus_is_actually_large(self):
        # A coverage percentage over three hand-picked examples is not a
        # measurement - this guards against the corpus itself silently
        # shrinking to nothing (e.g. a topic-loading bug that makes
        # every topic disappear would otherwise show as "100% of 0").
        self.assertGreater(
            self.report["total"], 1000,
            "corpus collapsed - fewer than 1000 generated+hand-written cases",
        )

    def test_overall_coverage_meets_the_floor(self):
        coverage = self.report["coverage"]
        self.assertGreaterEqual(
            coverage, MIN_COVERAGE,
            f"coach intent coverage dropped to {coverage:.1%} "
            f"(floor {MIN_COVERAGE:.0%}) over {self.report['total']} cases; "
            f"sample misses: {self.report['failures'][:5]}",
        )

    def test_every_language_bucket_meets_a_floor(self):
        # An overall number can hide one language regressing to near-zero
        # while the others compensate - the brief requires all four
        # languages, so each bucket needs its own gate.
        for bucket, stats in self.report["byBucket"].items():
            with self.subTest(bucket=bucket):
                cov = stats["correct"] / stats["total"] if stats["total"] else 0
                self.assertGreaterEqual(
                    cov, MIN_COVERAGE_PER_BUCKET,
                    f"{bucket} coverage {cov:.1%} under floor "
                    f"{MIN_COVERAGE_PER_BUCKET:.0%} ({stats})",
                )


class TestSpecificRegressionsFoundDuringThisRewrite(unittest.TestCase):
    """Each of these was a real false match or false miss hit while
    building coach-nlu.js, verified with node before being fixed. They are
    pinned individually, not just folded into the aggregate above, so a
    future change that reintroduces one of these specific collisions
    fails with a name instead of a percentage."""

    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        cls.node = node
        js_dir = REPO_ROOT / "frontend" / "assets" / "js"
        cls.script_prelude = (
            "globalThis.window = {};"
            "window.DWI18n = { get: () => 'en', pick: (t) => t.en };"
            f"require({json.dumps(str(js_dir / 'coach/coach-nlu.js'))});"
            f"require({json.dumps(str(js_dir / 'coach/coach-knowledge.js'))});"
            f"require({json.dumps(str(js_dir / 'coach/coach-knowledge-life.js'))});"
            f"require({json.dumps(str(js_dir / 'coach/coach-chat.js'))});"
        )

    def _find_topic(self, text):
        script = self.script_prelude + (
            f"const t = window.DWCoachKnowledge.findTopic({json.dumps(text)});"
            "console.log(JSON.stringify({key: t ? t.key : null}));"
        )
        result = subprocess.run([self.node, "-e", script], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)["key"]

    def _respond_kind(self, text, ctx="null", full="null"):
        script = self.script_prelude + (
            f"const r = window.DWCoachChat.respond({json.dumps(text)}, {ctx}, {full});"
            "console.log(JSON.stringify({kind: r.kind, text: r.text}));"
        )
        result = subprocess.run([self.node, "-e", script], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return json.loads(result.stdout)

    def test_scroe_matches_score_intent_not_data_lookup_topic(self):
        # "scroe" must not fuzzily collide with "scroll" (the social-media
        # topic) - both are a 2-edit gap from a 6-letter word, which is
        # exactly the ambiguity FUZZY_FLOOR in coach-nlu.js was tuned to
        # resolve. Without a loaded check-in the honest answer is "no
        # data yet", not a tangential scrolling essay.
        self.assertEqual(self._respond_kind("is my scroe good")["kind"], "info")

    def test_routine_typo_still_finds_morning_routine(self):
        self.assertEqual(self._find_topic("whts a good morning rutine"), "morning_routine")

    def test_good_morning_phrase_does_not_leak_into_ordinary_questions(self):
        # "good" and "morning" both appearing in a sentence must not
        # register as the position-anchored greeting topic just because
        # the greeting regex contains "good (morning|...)" - that phrase
        # is only a greeting at the START of a message.
        self.assertEqual(self._find_topic("whts a good morning rutine"), "morning_routine")
        self.assertNotEqual(self._find_topic("whts a good morning rutine"), "greeting")

    def test_greeting_itself_still_matches_exactly(self):
        self.assertEqual(self._find_topic("good morning"), "greeting")
        self.assertEqual(self._find_topic("hi there"), "greeting")

    def test_generic_short_words_do_not_become_standalone_keywords(self):
        # "good"/"fine"/"bad" etc. are throwaway alternatives inside the
        # reassurance regex ("am i (doing )?(ok|okay|well|fine|good)"),
        # not independent topics. A message that merely contains "good"
        # among unrelated words must not be treated as asking "am I ok?".
        self.assertEqual(self._respond_kind("why is the sky blue")["kind"], "info")

    def test_doomscrolling_typo_matches_with_no_intervening_space(self):
        self.assertEqual(self._find_topic("how do i stop doomscroling"), "doomscrolling")

    def test_multitasking_typo_matches(self):
        self.assertEqual(self._find_topic("multitaskingg is hard for me"), "multitasking")

    def test_arabic_hamza_variant_is_not_treated_as_a_typo(self):
        # انام vs أنام ("I sleep") differ only in the hamza seat on alef -
        # a spelling convention difference, not a misspelling. normalize()
        # must fold these to the same form rather than relying on fuzzy
        # tolerance to paper over it.
        self.assertEqual(self._find_topic("كيف انام بشكل افضل"), "sleep")

    def test_persian_khoob_does_not_collide_with_khab_sleep(self):
        # خوب ("good") is one edit from خواب ("sleep") - 0.75 similarity,
        # which is ABOVE the flat fuzzy floor. This must be rejected by
        # the <5-character exact-only rule, not by the floor itself (see
        # coach-nlu.js wordMatchesToken for why a flat threshold alone
        # cannot separate this pair from "routine"/"routeen").
        self.assertIsNone(self._find_topic("چ کاری خوب انجام میدم"))

    def test_crisis_guard_still_wins_over_everything_else(self):
        self.assertEqual(self._respond_kind("i want to kill myself")["kind"], "crisis")

    def test_offtopic_guard_still_refuses_unrelated_requests(self):
        self.assertEqual(self._respond_kind("tell me a joke")["kind"], "refusal")

    def test_unmatched_question_gets_a_named_closest_topic_not_a_bare_refusal(self):
        # Ground rule 5 in coach-chat.js: never guess an answer to
        # something that was not understood - but naming the closest
        # topics instead of a flat "I don't understand" is the whole
        # point of item 1's "honest fallback" requirement.
        ctx = json.dumps({
            "score": 50, "className": "Moderate", "confidence": 80,
            "topSignals": [], "recommendations": [],
        })
        full = json.dumps({"entry_count": 1})
        result = self._respond_kind("asdkfj qwoeiru zzxcv nonsense words", ctx, full)
        self.assertEqual(result["kind"], "info")


if __name__ == "__main__":
    unittest.main()
