"""
Tests: onboarding is one question per slide, and the schedule question
is not one preference among three.

Why it changed. The three onboarding questions used to sit stacked on a
single screen, which reads as a form to get through. The schedule
answer is the one that actually changes behaviour - it decides which
signals count as problems for that user and which themes the weekly
plan reaches for first (services/wellness/improvement_plan_service.py's
_IRREGULAR_SCHEDULES / _IRREGULAR_BOOST) - and the note explaining that
was never going to be read three questions down a scroll.

What is pinned here:

  - one question per slide, one visible at a time, with a way back. A
    wizard you cannot reverse turns a mis-tap into a wrong answer
    stored for good. There are six now, not three: the pace, the
    work-screen question and the sleep window used to be submitted
    hard-coded by the client and read by nobody, which is a
    questionnaire with no reader. They are asked, and each changes the
    plan - see tests/wellness/test_onboarding_answers_matter.py;
  - the schedule slide carries its weight ON the question, not only in
    the guide;
  - the same emphasis appears on the profile page, which is where these
    answers are edited later - the all-at-once form still lives there
    on purpose;
  - the tour runs itself exactly ONCE, on the first screen after
    signing up. Everywhere else in this app the guide waits to be asked
    (see shell.js), so an automatic tour needs to be the deliberate
    exception it is, and it must not fire again on a reload;
  - four languages, as everything user-facing here is.

Run: python3 -m unittest tests.frontend.test_onboarding_slides -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

# The one definition of the project root - see core/paths.py. Every test
# used to recompute it from its own depth, which is exactly what would
# have broken - silently, by asserting over empty lists - the moment
# this tree grew folders.
from core import paths

REPO_ROOT = paths.PROJECT_ROOT
FRONTEND = REPO_ROOT / "frontend"
JS = FRONTEND / "assets" / "js"
CSS = FRONTEND / "assets" / "css"

LANGS = ("en", "fa", "ar", "zh")


class TestOnboardingSlides(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app_js = (JS / "pages/app.js").read_text(encoding="utf-8")
        cls.guide_js = (JS / "guide/guide-tips.js").read_text(encoding="utf-8")
        cls.i18n_js = (JS / "core/i18n.js").read_text(encoding="utf-8")
        cls.app_html = (FRONTEND / "app.html").read_text(encoding="utf-8")
        cls.profile_html = (FRONTEND / "profile.html").read_text(encoding="utf-8")
        cls.app_css = (CSS / "app.css").read_text(encoding="utf-8")

    # ----------------------------------------------------------- slides
    def test_every_question_has_its_own_slide(self):
        found = sorted(
            re.findall(r'data-onboard-slide="(\d+)"', self.app_html), key=int,
        )
        self.assertEqual(found, [str(i) for i in range(len(found))],
                         "the slide indices have a gap in them")
        self.assertIn(
            f"const ONBOARD_SLIDES = {len(found)};", self.app_js,
            f"the markup has {len(found)} slides but the script walks a "
            f"different number, so the last question is unreachable or the "
            f"Next button dead-ends on an empty screen",
        )

    def test_the_four_answers_that_were_hard_coded_are_asked_for_real(self):
        """The client used to submit "moderate", "23:00", "07:00" and
        "not required" on everybody's behalf. Each has a control now."""
        for marker in ('id="effortOptions"', 'id="workScreenOptions"',
                       'id="onboardSleepTime"', 'id="onboardWakeTime"'):
            self.assertIn(marker, self.app_html, f"{marker} is not on the page")
        # And the submit reads them rather than sending a constant.
        self.assertIn("state.onboard.effort", self.app_js)
        self.assertIn("state.onboard.workScreen", self.app_js)
        self.assertNotIn("usual_sleep_time: '23:00'", self.app_js)
        self.assertNotIn("preferred_effort: 'moderate',", self.app_js)

    def test_only_the_first_slide_starts_visible(self):
        slides = re.findall(
            r'<div class="onboard-slide([^"]*)" data-onboard-slide="(\d+)"',
            self.app_html,
        )
        self.assertGreaterEqual(len(slides), 3)
        for classes, index in slides:
            if index == "0":
                self.assertNotIn("hidden", classes)
            else:
                self.assertIn("hidden", classes, f"slide {index} starts visible")

    def test_the_wizard_can_be_reversed(self):
        # A mis-tap on "next" must not be a wrong answer stored for good.
        self.assertIn('id="onboardBack"', self.app_html)
        self.assertIn("state.onboardSlide -= 1", self.app_js)

    def test_save_only_appears_on_the_last_slide(self):
        body = self.app_js[self.app_js.index("function renderOnboardSlide"):]
        body = body[:body.index("\n  function wireOnboarding")]
        self.assertIn("const last = state.onboardSlide === ONBOARD_SLIDES - 1;", body)
        self.assertIn("$('#onboardSave').classList.toggle('hidden', !last)", body)
        self.assertIn("$('#onboardNext').classList.toggle('hidden', last)", body)

    def test_reopening_onboarding_starts_at_the_first_slide(self):
        body = self.app_js[self.app_js.index("function renderOnboarding"):]
        body = body[:body.index("\n  /* Onboarding is one question per slide")]
        self.assertIn("state.onboardSlide = 0;", body)
        self.assertIn("renderOnboardSlide();", body)

    def test_the_progress_row_shows_where_you_are(self):
        self.assertIn('id="onboardProgress"', self.app_html)
        self.assertIn("onboard-dot", self.app_js)
        self.assertIn(".onboard-dot.active", self.app_css)

    def test_the_slides_respect_reduced_motion(self):
        idx = self.app_css.index(".onboard-slide {")
        tail = self.app_css[idx:idx + 600]
        self.assertIn("prefers-reduced-motion", tail)
        self.assertIn("force-reduce-motion", tail)

    # ------------------------------------------------- schedule emphasis
    def test_the_schedule_question_carries_its_weight_on_the_question(self):
        self.assertIn('data-i18n="onboard_schedule_weight"', self.app_html)
        self.assertIn("onboard-emphasis", self.app_css)

    def test_the_emphasis_sits_with_the_schedule_question_and_no_other(self):
        # Under goal or purpose it would be simply false - those two do
        # not change which signals count as problems.
        idx = self.app_html.index('data-i18n="onboard_schedule_weight"')
        preceding = self.app_html[:idx]
        self.assertGreater(
            preceding.rindex('id="scheduleOptions"'),
            preceding.rindex('id="purposeOptions"'),
        )

    def test_the_schedule_slide_is_wired_to_the_guide(self):
        self.assertIn('data-guide="schedule_regularity"', self.app_html)

    def test_the_profile_page_carries_the_same_emphasis(self):
        # The all-at-once form still lives there, on purpose: it is
        # where these answers are edited later. The weight has to travel
        # with the question.
        self.assertIn('data-i18n="onboard_schedule_weight"', self.profile_html)

    def test_the_emphasis_exists_in_all_four_languages(self):
        found = len(re.findall(r"\bonboard_schedule_weight\s*:", self.i18n_js))
        self.assertEqual(found, len(LANGS))

    def test_the_emphasis_is_not_english_in_every_language(self):
        values = re.findall(
            r"\bonboard_schedule_weight\s*:\s*(['\"])(.*?)\1", self.i18n_js, re.S,
        )
        texts = [v[1] for v in values]
        self.assertEqual(len(texts), len(LANGS))
        self.assertEqual(len(set(texts)), len(LANGS), texts)

    # ----------------------------------------------------- the first run
    def test_the_tour_runs_itself_after_the_preferences_are_answered(self):
        """It used to fire when the onboarding view OPENED, so the guide
        talked over the first preference question it was introducing. It
        now waits until the answers are in - or until the user skips
        them, which is more reason to be shown around, not less."""
        self.assertIn("localStorage.setItem(FIRST_RUN_KEY, '1')", self.app_js)
        self.assertIn("maybeRunFirstRunTour();", self.app_js)
        self.assertIn("startTour('welcome'", self.app_js)

        # Anchored on the LISTENER, not the first mention of the id -
        # the button is also referenced by renderOnboardSlide, and a
        # slice from there measures the wrong function.
        save_handler = self.app_js[
            self.app_js.index("$('#onboardSave').addEventListener"):
        ]
        self.assertIn(
            "maybeRunFirstRunTour();", save_handler[:2200],
            "the tour does not run once the preferences are saved",
        )
        skip_handler = self.app_js[self.app_js.index("$('#onboardSkip').addEventListener"):]
        self.assertIn("maybeRunFirstRunTour();", skip_handler[:400])

    def test_the_tour_can_be_left(self):
        """It arrives uninvited, so leaving it has to be one visible
        click. The previous version queued every step as a timeout up
        front, which meant "skip" could hide the current bubble and then
        be talked over by the next seven."""
        guide = (JS / "guide/guide-tips.js").read_text(encoding="utf-8")
        self.assertIn("function stopTour()", guide)
        self.assertIn("dwTourSkip", guide)
        self.assertIn("stopTour", guide[guide.index("window.DWGuide = "):])
        # Chained, not queued: exactly one pending timer at a time.
        tour = guide[guide.index("function startTour("):]
        self.assertIn("setTimeout(next, step)", tour)

    def test_the_flag_is_set_before_the_screen_is_rendered(self):
        # afterLogin() is what renders onboarding, and the flag is what
        # tells it to run the tour. Setting it afterwards would be too
        # late and the tour would never fire.
        idx = self.app_js.index("localStorage.setItem(FIRST_RUN_KEY, '1')")
        after = self.app_js[idx:idx + 200]
        self.assertIn("await afterLogin();", after)

    def test_the_tour_fires_exactly_once(self):
        body = self.app_js[self.app_js.index("function maybeRunFirstRunTour"):]
        body = body[:body.index("\n  function buildOptionList")] \
            if "\n  function buildOptionList" in body else body[:1200]
        self.assertIn("localStorage.removeItem(FIRST_RUN_KEY)", body)
        self.assertIn("if (!pending", body)

    def test_an_onboarding_tour_actually_exists_to_run(self):
        # startTour() returns false for an unknown page key, which would
        # make the whole first-run path a silent no-op.
        self.assertIn("onboarding: ['onboarding_intro', 'schedule_regularity']", self.guide_js)

    def test_both_tour_topics_have_text_in_all_four_languages(self):
        for topic in ("onboarding_intro", "schedule_regularity"):
            found = len(re.findall(rf"\b{topic}\s*:\s*['\"]", self.guide_js))
            self.assertEqual(found, len(LANGS), f"{topic} is not in all four languages")

    def test_the_tour_topics_are_registered_with_valid_faces(self):
        # An unregistered topic falls back to defaults silently; a face
        # that does not exist renders nothing at all.
        self.assertIn("onboarding_intro:", self.guide_js)
        valid = {"borderline", "confused", "good", "great", "neutral", "risk", "thinking"}
        match = re.search(r"onboarding_intro:\s*\{\s*face:\s*'([a-z]+)'", self.guide_js)
        self.assertIsNotNone(match)
        self.assertIn(match.group(1), valid)


if __name__ == "__main__":
    unittest.main()
