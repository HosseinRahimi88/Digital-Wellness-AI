"""The coach conversations a demo user has already had.

A demo could hand a reviewer twenty-three days of history, a weekly plan
three weeks in, badges, a League and a violation ledger - and an AI Coach
with an empty thread list, as though this person had lived with the app
for a month and never asked it anything.

What this pins:

  · every scripted question, in all four languages, reaches a REAL
    answer through the real matcher. A thread whose reply is "I'm not
    sure I follow" makes the coach look broken rather than empty, so the
    node runner below loads the actual frontend files and calls the
    actual respond();
  · every one of the thirty-two states gets several threads, and the
    lapsed half gets the ones only a lapsed user would ask;
  · the answers are GENERATED, not stored. There is no transcript in the
    repo to drift away from what the coach says, because the seeder
    calls respond() itself;
  · a real account is never seeded, and a re-seed removes only the
    seeder's own threads.

The language coverage this exposed was a genuine bug, fixed alongside:
the coach's five personal-data intents (score / first / topic /
strength / why), its trend hints and its self-reference test were
English with a little Persian, so Arabic and Chinese users could not
reach their own numbers at all. Chinese had a second failure on top -
respond() called any message of two "words" or fewer too short to act
on, and Chinese does not put spaces between words, so EVERY Chinese
message counted as one.

Run: python3 -m unittest tests.test_demo_coach_chats -v
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve().parent / "js" / "demo_coach_chats_runner.js"
JS = REPO_ROOT / "frontend" / "assets" / "js"

LANGS = ("en", "fa", "ar", "zh")


class TestDemoCoachChatsAnswer(unittest.TestCase):
    """Executed under node against the real frontend files."""

    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        result = subprocess.run(
            [node, str(RUNNER), str(REPO_ROOT)],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            raise AssertionError(f"runner failed:\n{result.stderr}")
        cls.report = json.loads(result.stdout)

    def test_every_question_reaches_a_real_answer(self):
        failures = self.report["failures"]
        self.assertEqual(
            failures, [],
            "these scripted questions land on a fallback instead of an answer:\n"
            + "\n".join(f"  [{f['lang']}] {f.get('q', f['thread'])} -> {f['why']}" for f in failures),
        )

    def test_a_meaningful_number_of_questions_was_checked(self):
        # Four languages times the whole script. A collapse to a handful
        # would mean the runner stopped finding the threads rather than
        # that everything passed.
        self.assertGreaterEqual(self.report["checked"], 100)

    def test_every_one_of_the_thirty_two_states_gets_several_threads(self):
        counts = self.report["threadCounts"]
        self.assertEqual(len(counts), 32, "the catalogue is four profiles x four lengths x the lapsed tick")
        for state, count in counts.items():
            self.assertGreaterEqual(count, 4, f"{state} has too few threads to be worth opening")

    def test_a_lapsed_state_has_threads_a_clean_one_does_not(self):
        counts = self.report["threadCounts"]
        for state, count in counts.items():
            if state.endswith(":lapsed"):
                twin = state.replace(":lapsed", ":clean")
                self.assertNotEqual(
                    count, 0, f"{state} has no threads at all",
                )
                self.assertIn(twin, counts)


class TestDemoCoachChatsSource(unittest.TestCase):
    """The rules that keep this from touching a real user's threads."""

    @classmethod
    def setUpClass(cls):
        cls.seeder = (JS / "coach-demo-chats.js").read_text(encoding="utf-8")
        cls.store = (JS / "coach-conversations.js").read_text(encoding="utf-8")
        cls.coach = (JS / "coach.js").read_text(encoding="utf-8")
        cls.demo = (JS / "demo.js").read_text(encoding="utf-8")
        cls.page = (REPO_ROOT / "frontend" / "coach.html").read_text(encoding="utf-8")

    def test_nothing_is_written_without_a_demo_state(self):
        # The first thing ensure() does. Without it, a real user opening
        # the coach would find six conversations they never had.
        body = self.seeder[self.seeder.index("async function ensure()"):]
        head = body[:body.index("const store")]
        self.assertIn("demoState()", head)
        self.assertIn("if (!state) return 0", head)

    def test_the_answers_come_from_the_real_responder(self):
        """No stored transcripts: the point of the whole file."""
        self.assertIn("chat.respond(text, ctx, full)", self.seeder)
        self.assertIn("chat.loadContext()", self.seeder)
        self.assertIn("window.DWCoachContext.load", self.seeder)

    def test_no_answer_text_is_hardcoded(self):
        """A demo thread must not contain a written-out reply. `asks`
        entries are questions; an `answer`/`reply` key would mean
        somebody started shipping canned text."""
        self.assertNotIn("answer:", self.seeder)
        self.assertNotIn("reply:", self.seeder)

    def test_only_its_own_threads_are_removed(self):
        self.assertIn("store.removeMarked(MARKER)", self.seeder)
        self.assertNotIn("clearAll()", self.seeder)
        self.assertIn("function removeMarked(marker)", self.store)
        self.assertIn("readAll().filter((c) => c.marker !== marker)", self.store)

    def test_a_seeded_thread_records_the_language_it_was_written_in(self):
        self.assertIn("lang: current", self.seeder)
        self.assertIn("mine.every((c) => c.lang === current)", self.seeder)

    def test_nothing_is_seeded_when_there_is_no_data_to_answer_from(self):
        """Six threads of "I don't have a check-in to work from yet" is
        a worse first impression than an empty list.

        The emptiness test has to be isEmpty(), not truthiness:
        DWCoachContext.load() resolves to enrich(cached || {}) and hands
        back an object even when the fetch failed, so `!full` alone
        would never be true and the guard would never fire.
        """
        self.assertIn("if (!ctx && digestEmpty) return 0;", self.seeder)
        self.assertIn("window.DWCoachContext.isEmpty(full)", self.seeder)

    def test_threads_are_dated_across_the_users_own_history(self):
        self.assertIn("function whenFor(", self.seeder)
        self.assertIn("86400000", self.seeder)

    def test_the_seeder_is_wired_into_the_coach_page(self):
        self.assertIn("coach-demo-chats.js", self.page)
        self.assertIn("coach-knowledge-plan.js", self.page)
        self.assertIn("window.DWCoachDemoChats.ensure()", self.coach)

    def test_leaving_a_demo_drops_its_threads(self):
        """The demo account is deleted; its threads are keyed by that
        account id and would otherwise be unreachable but still stored."""
        self.assertIn("window.DWCoachConversations.clearAll()", self.demo)

    def test_the_lapsed_flag_survives_into_the_demo_state(self):
        self.assertIn("lapsed: !!session.with_violations", self.demo)
        self.assertIn("state", self.demo[self.demo.index("window.DWDemo = {"):])

    def test_every_thread_is_named_in_four_languages(self):
        """A thread list of "New conversation" x6 is not a demo."""
        titles = re.findall(r"title: \{(.*?)\}", self.seeder, re.S)
        self.assertGreaterEqual(len(titles), 8)
        for block in titles:
            for lang in LANGS:
                self.assertIn(f"{lang}:", block)


class TestPlanKnowledgeBase(unittest.TestCase):
    """The weekly plan's own rules, which had no coach coverage at all.

    Asked "why was a badge taken away from me?", the coach used to reach
    for the nearest thing it knew and explain SHAP - an answer to a
    different question, delivered confidently.
    """

    @classmethod
    def setUpClass(cls):
        cls.kb = (JS / "coach-knowledge-plan.js").read_text(encoding="utf-8")

    def test_the_rules_that_cost_the_user_something_are_all_covered(self):
        for key in (
            "plan_day_colours",        # grey/orange/red and what each costs
            "plan_penalty_and_score",  # and that it is NOT taken off the score
            "plan_missed_day",
            "plan_what_is_violation",
            "plan_badge_revoked",
            "plan_days_in_order",
            "plan_one_checkin_a_day",
            "plan_exception_day",
            "plan_locked_to_the_week",
            "plan_next_week",
        ):
            self.assertIn(f"key: '{key}'", self.kb)

    def test_every_entry_answers_in_four_languages(self):
        entries = re.findall(r"key: '(\w+)'", self.kb)
        self.assertGreaterEqual(len(entries), 10)
        for lang in LANGS:
            self.assertEqual(
                len(re.findall(rf"\n      {lang}: ", self.kb)), len(entries),
                f"an entry is missing its {lang} answer",
            )

    def test_the_colour_answer_states_the_actual_penalties(self):
        block = self.kb[self.kb.index("key: 'plan_day_colours'"):]
        block = block[:block.index("key: 'plan_penalty_and_score'")]
        self.assertIn("half a point", block)
        self.assertIn("a full point", block)
        # The two halves are equal on purpose; an answer that ranked them
        # would be making a judgement the app has no basis for.
        self.assertIn("deliberately equal", block)

    def test_the_patterns_use_flat_alternatives_only(self):
        """extractKeywords() splits on EVERY `|` with no bracket
        awareness, so a nested alternation yields fragments that match
        nothing. `(?:s|es|ing)?` is the one sanctioned exception, same
        as coach-knowledge-app.js."""
        for source in re.findall(r"match: /(.+?)/i,", self.kb):
            stripped = source.replace("(?:s|es|ing)?", "")
            depth = 0
            for i, ch in enumerate(stripped):
                if ch == "(" and (i == 0 or stripped[i - 1] != "\\"):
                    depth += 1
                elif ch == ")" and stripped[i - 1] != "\\":
                    depth -= 1
                elif ch == "|" and depth > 1:
                    self.fail(f"nested alternation in: {source[:60]}")

    def test_it_is_registered_like_the_other_knowledge_files(self):
        self.assertIn("window.DWCoachKnowledge.register(TOPICS, { priority: 10 })", self.kb)
        self.assertIn("if (!window.DWCoachKnowledge || !window.DWCoachKnowledge.register) return;", self.kb)


class TestCoachLanguageParity(unittest.TestCase):
    """Arabic and Chinese could not reach the coach's personal answers.

    The five "about my own data" intents were written out twice - once
    inline in respond() for the exact path, once in dataLookupIntents()
    for the fuzzy one - and both copies were English plus a little
    Persian. Now one named constant each, so a language added to a
    question is added to both paths at once.
    """

    @classmethod
    def setUpClass(cls):
        cls.chat = (JS / "coach-chat.js").read_text(encoding="utf-8")

    def test_the_five_intents_have_one_definition_each(self):
        for name in ("ASK_SCORE", "ASK_FIRST", "ASK_STRENGTH", "ASK_WHY"):
            self.assertEqual(
                len(re.findall(rf"const {name} = ", self.chat)), 1,
                f"{name} should be defined exactly once",
            )
            # Used by both paths.
            self.assertGreaterEqual(len(re.findall(rf"\b{name}\b", self.chat)), 3)

    def test_every_intent_covers_all_four_languages(self):
        arabic_only = re.compile(r"[ء-ي]")
        cjk = re.compile(r"[一-鿿]")
        for name in ("ASK_SCORE", "ASK_FIRST", "ASK_SLEEP", "ASK_STRENGTH", "ASK_WHY"):
            line = re.search(rf"const {name} = /(.+?)/i;", self.chat).group(1)
            self.assertTrue(arabic_only.search(line), f"{name} has no Arabic alternative")
            self.assertTrue(cjk.search(line), f"{name} has no Chinese alternative")

    def test_self_reference_recognises_arabic_and_chinese(self):
        line = re.search(r"const SELF_REFERENCE = /(.+?)/i;", self.chat).group(1)
        self.assertIn("我", line)
        self.assertIn("درجتي", line)

    def test_a_chinese_question_is_not_treated_as_too_short(self):
        """Chinese has no spaces, so the "two words or fewer" nudge fired
        on every Chinese message however long and specific."""
        self.assertIn("const cjk = (q.match(/[一-鿿]/g) || []).length;", self.chat)
        self.assertIn("cjk ? Math.ceil(cjk / 2)", self.chat)

    def test_a_long_unmatched_chinese_message_gets_the_real_fallback(self):
        """The behaviour behind the line above, measured rather than
        asserted about the source: a long Chinese message that matches
        nothing should get the fallback that names the closest topics,
        not the nudge meant for someone who typed two words."""
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not available")
        result = subprocess.run(
            [node, str(RUNNER), str(REPO_ROOT)],
            capture_output=True, text=True, timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            json.loads(result.stdout)["cjkNudgeBug"],
            "a long Chinese question is being told to say more",
        )

    def test_the_trend_hints_cover_all_four_languages(self):
        block = self.chat[self.chat.index("const TREND_HINTS = ["):]
        block = block[:block.index("];")]
        self.assertIn("趋势", block)
        self.assertIn("بمرور الوقت", block)
        # Persian only had the past tense, so "am I getting better" missed.
        self.assertIn("بهتر می ?شوم", block)


class TestTrendIsAnsweredFromTheHistoryItHas(unittest.TestCase):
    """The coach refused a question whose answer was in its own argument.

    "Am I improving?" returned "I only have your most recent check-in
    loaded here, not your history" - a sentence that predates
    coach-context.js and has been false since. The server digest passed
    in as `full` carries the entry count, the 7-day change, the streak,
    the range and a per-signal trend list.
    """

    @classmethod
    def setUpClass(cls):
        cls.chat = (JS / "coach-chat.js").read_text(encoding="utf-8")

    def test_there_is_a_real_trend_answer(self):
        self.assertIn("function trendAnswer(full)", self.chat)
        self.assertIn("full.score_change_7d", self.chat)
        self.assertIn("full.trends", self.chat)

    def test_it_still_refuses_when_there_genuinely_is_no_history(self):
        block = self.chat[self.chat.index("function trendAnswer(full)"):]
        self.assertIn("if (!full || (full.entry_count || 0) < 2) return null;", block[:400])
        # And the caller falls back to the honest refusal on null.
        self.assertIn("return { text: c.trendUnavailable, kind: 'info' };", self.chat)

    def test_it_is_checked_before_the_no_local_checkin_branch(self):
        """Someone signing in on a second device has a full history on
        the server and nothing in this browser; "I have no data" would
        be the wrong answer for them."""
        trend_at = self.chat.index("const trend = trendAnswer(full);")
        no_ctx_at = self.chat.index("if (!ctx) {\n      const general = knowledgeAnswer(q);")
        self.assertLess(trend_at, no_ctx_at)

    def test_a_short_history_is_labelled_as_a_direction_not_a_verdict(self):
        block = self.chat[self.chat.index("function trendAnswer(full)"):]
        self.assertIn("full.entry_count < 7", block[:4000])


if __name__ == "__main__":
    unittest.main()
