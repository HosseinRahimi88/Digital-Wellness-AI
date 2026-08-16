"""Section E games: G4 (insufficient data never renders) and G6 (all
four languages), for every game in the real frontend/assets/js/games.js -
the five that shipped before this round plus the six added when games
moved to their own screen between processing and the result.

Runs the actual file under node (tests/js/games_eligibility_runner.js),
same established pattern as tests/test_badge_service.py and
tests/test_coach_nlu_coverage.py, so a change to the real matcher logic
is what this test sees - not a Python re-implementation of it.

Deliberately checks BOTH directions per the project's own testing habit
(see HANDOFF.md: "verify checkers against known-broken input"): an empty
context must make every game ineligible (G4), and a context with
everything present must make every game eligible - otherwise a bug in
eligible() that always returns false would pass the G4 check vacuously.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve().parent / "js" / "games_eligibility_runner.js"

EXPECTED_NEW_GAMES = {
    "game_dimension_duel", "game_confidence_guess", "game_future_class_guess",
    "game_weekday_or_weekend", "game_badge_race", "game_score_vs_average",
}
EXPECTED_ORIGINAL_GAMES = {
    "game_guess_score", "game_which_factor", "game_baseline_or_exception",
    "game_fill_the_blank", "game_keep_the_streak",
}

# 'pre': the game's own reveal shows a number (score, confidence) that
# has not appeared on screen yet, so it must run before the result view.
# 'post': everything else - each reads secondary context (SHAP factors,
# streak, badges, historical stats) that does not spoil anything and is
# written assuming the result is already visible.
EXPECTED_PRE_GAMES = {"game_guess_score", "game_confidence_guess", "game_score_vs_average"}
EXPECTED_POST_GAMES = (EXPECTED_NEW_GAMES | EXPECTED_ORIGINAL_GAMES) - EXPECTED_PRE_GAMES


class TestGamesEligibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        result = subprocess.run(
            [node, str(RUNNER), str(REPO_ROOT)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise AssertionError("games_eligibility_runner.js failed: " + result.stderr)
        cls.report = json.loads(result.stdout)
        cls.by_key = {r["key"]: r for r in cls.report["results"]}

    def test_all_eleven_games_are_present(self):
        self.assertEqual(self.report["count"], 11)
        self.assertEqual(set(self.by_key), EXPECTED_ORIGINAL_GAMES | EXPECTED_NEW_GAMES)

    def test_every_game_refuses_to_render_on_insufficient_data(self):
        # G4. A game that renders on an empty context would show up with
        # nothing real to say.
        offenders = [k for k, r in self.by_key.items() if r["emptyContextEligible"] is not False]
        self.assertEqual(offenders, [], f"eligible({{}}) was not exactly false for: {offenders}")

    def test_every_game_can_actually_become_eligible(self):
        # The other direction of the check above: a checker that always
        # returns false would also pass "insufficient data never
        # renders" - vacuously. Each game must be reachable given real
        # enough data.
        offenders = [k for k, r in self.by_key.items() if r["fullContextEligible"] is not True]
        self.assertEqual(offenders, [], f"eligible(<rich context>) was not true for: {offenders}")

    def test_every_game_declares_all_four_languages(self):
        # G6.
        offenders = {k: r["missingTitleLanguages"] for k, r in self.by_key.items() if r["missingTitleLanguages"]}
        self.assertEqual(offenders, {}, f"games missing a title language: {offenders}")

    def test_every_game_is_tagged_pre_or_post(self):
        # F5: the report a user has to guess about (score, confidence)
        # must not appear on screen before they guess it. A game with no
        # phase at all, or an unrecognised one, is a silent gap - it
        # would fall through both the pre-result and post-result render
        # calls (each filters by an explicit phase) and never show.
        self.assertEqual(self.report["untagged"], [])
        self.assertEqual(self.report["preCount"], len(EXPECTED_PRE_GAMES))
        self.assertEqual(self.report["postCount"], len(EXPECTED_POST_GAMES))
        actual_pre = {k for k, r in self.by_key.items() if r["phase"] == "pre"}
        actual_post = {k for k, r in self.by_key.items() if r["phase"] == "post"}
        self.assertEqual(actual_pre, EXPECTED_PRE_GAMES)
        self.assertEqual(actual_post, EXPECTED_POST_GAMES)

    def test_render_phase_filter_only_considers_its_own_phase(self):
        # Calls the real render() (via a spied eligible(), see the
        # runner) rather than re-deriving the filter here - this is the
        # function app.js actually calls for both the pre-result and the
        # post-result mount.
        self.assertEqual(sorted(self.report["preCandidates"]), sorted(EXPECTED_PRE_GAMES))
        self.assertEqual(sorted(self.report["postCandidates"]), sorted(EXPECTED_POST_GAMES))

    def test_every_game_has_a_guide_topic(self):
        offenders = [k for k, r in self.by_key.items() if not r["hasGuideTopic"]]
        self.assertEqual(offenders, [], f"games with no guideTopic: {offenders}")


class TestGamesPageWiring(unittest.TestCase):
    """The placement change (HANDOFF item 2, 3-b): games now live on
    their own screen between processing and the result, not on the
    dashboard or at the bottom of the result page."""

    @classmethod
    def setUpClass(cls):
        cls.app_html = (REPO_ROOT / "frontend" / "app.html").read_text(encoding="utf-8")
        cls.dashboard_html = (REPO_ROOT / "frontend" / "dashboard.html").read_text(encoding="utf-8")
        cls.games_js = (REPO_ROOT / "frontend" / "assets" / "js" / "games.js").read_text(encoding="utf-8")
        cls.app_js = (REPO_ROOT / "frontend" / "assets" / "js" / "app.js").read_text(encoding="utf-8")
        cls.app_chrome_js = (REPO_ROOT / "frontend" / "assets" / "js" / "app-chrome.js").read_text(encoding="utf-8")

    def test_the_games_view_exists_between_predict_and_result(self):
        predict_pos = self.app_html.index('id="view-predict"')
        games_pos = self.app_html.index('id="view-games"')
        result_pos = self.app_html.index('id="view-result"')
        self.assertTrue(predict_pos < games_pos < result_pos)

    def test_the_games_view_has_a_mount_and_a_continue_button(self):
        self.assertIn('id="gamesPageMount"', self.app_html)
        self.assertIn('id="gamesContinueBtn"', self.app_html)

    def test_the_result_page_no_longer_has_its_own_games_mount(self):
        # This is the OLD mount, from the scheme where every game sat at
        # the bottom of the result page regardless of phase (HANDOFF item
        # 2, 3-b). It must not come back. `gamesAfterMount` (below) is a
        # narrower, deliberate replacement: only the 'post' games render
        # there, and only after the reader has already seen the result.
        self.assertNotIn('id="resultGamesMount"', self.app_html)

    def test_the_result_page_has_the_post_phase_games_mount(self):
        # F5: games whose own text assumes the result is already visible
        # (e.g. future_class_guess: "You already saw today's score")
        # render further down the result page, in their own section that
        # starts hidden and is only revealed if games.js finds one
        # eligible - never an empty heading with nothing under it.
        self.assertIn('id="gamesAfterMount"', self.app_html)
        self.assertIn('id="gamesAfterSection"', self.app_html)
        section_pos = self.app_html.index('id="gamesAfterSection"')
        section_tag_start = self.app_html.rindex("<div", 0, section_pos)
        section_tag_end = self.app_html.index(">", section_tag_start)
        section_tag = self.app_html[section_tag_start:section_tag_end]
        self.assertIn("games-section", section_tag)
        self.assertIn("hidden", section_tag)
        # Must sit inside view-result, after the pre-result games view -
        # otherwise it would be reachable before the result exists.
        games_view_pos = self.app_html.index('id="view-games"')
        result_view_pos = self.app_html.index('id="view-result"')
        self.assertTrue(games_view_pos < result_view_pos < section_pos)

    def test_the_dashboard_no_longer_has_a_games_mount(self):
        self.assertNotIn('id="dashGamesMount"', self.dashboard_html)

    def test_games_can_be_switched_off_and_default_on(self):
        self.assertIn("isEnabled", self.games_js)
        self.assertIn("setEnabled", self.games_js)
        # Opt-out, not opt-in (G2 spirit: the existing feature keeps
        # working for everyone who never touches the new switch).
        self.assertIn("!== '0'", self.games_js)

    def test_the_settings_switch_exists_and_is_wired(self):
        self.assertIn('id="settingsGamesSwitch"', self.app_chrome_js)
        self.assertIn("settingsGamesSwitch", self.app_chrome_js)
        self.assertIn("DWGames.setEnabled", self.app_chrome_js)

    def test_no_page_ships_a_rival_settings_modal(self):
        """This used to assert that app.html's OWN static copy of the
        settings panel carried the games switch too, because the two
        must not drift.

        They drifted anyway. app.html's copy never gained the Digital
        guide section, and since ensureSettingsModal() reuses whatever
        #settingsModal it finds, that stale copy won on the check-in
        page and the guide's switches were unreachable from it -
        reported as "the coach settings are only on the dashboard".

        The copy is gone, so the guard is now the stronger one: there is
        exactly one definition of this panel, and drift is not possible.
        The games switch itself is asserted in the template by
        test_the_settings_switch_exists_and_is_wired above.
        """
        self.assertNotIn(
            'id="settingsModal"', self.app_html,
            "app.html is carrying its own settings panel again - "
            "ensureSettingsModal() will prefer it and it will drift",
        )

    def test_the_request_is_not_delayed_for_games(self):
        # The prediction must be awaited and stored BEFORE any games
        # logic runs, and games logic itself must be gated on
        # DWGames.isEnabled() rather than unconditionally awaited before
        # the result can show.
        predict_pos = self.app_js.index("window.DWApi.predict(")
        games_pos = self.app_js.index("await buildGamesContext(result)")
        self.assertTrue(predict_pos < games_pos)
        self.assertIn("window.DWGames.isEnabled()", self.app_js)

    def test_nothing_eligible_skips_straight_to_the_result(self):
        # Renamed from gamesShown when the pre/post split was added
        # (F5) - this now gates only the pre-result view-games screen.
        # Zero eligible 'post' games is handled separately: the section
        # simply stays hidden (see test_the_result_page_has_the_post_phase_games_mount).
        self.assertIn("preGamesShown > 0", self.app_js)

    def test_both_render_calls_are_phase_scoped(self):
        # F5's actual requirement: the pre-result mount only ever gets
        # 'pre' games (which guess a number not yet on screen) and the
        # post-result mount only ever gets 'post' games (which assume
        # the reader has already seen the result). Getting this backwards
        # would put "You already saw today's score" in front of someone
        # who has not.
        pre_call = self.app_js.index("$('#gamesPageMount')")
        pre_call_end = self.app_js.index(";", pre_call)
        self.assertIn("phase: 'pre'", self.app_js[pre_call:pre_call_end])

        post_call = self.app_js.index("$('#gamesAfterMount')")
        post_call_end = self.app_js.index(";", post_call)
        self.assertIn("phase: 'post'", self.app_js[post_call:post_call_end])

    def test_post_games_render_only_after_the_result_view_is_shown(self):
        # The post-result render call must live inside showResult (after
        # showView('view-result')), not run in parallel with it - the
        # section it targets does not exist as visible content until
        # then, and showing it earlier would be the exact bug this
        # section fixes for future_class_guess.
        show_result_pos = self.app_js.index("const showResult = () =>")
        show_view_pos = self.app_js.index("showView('view-result')", show_result_pos)
        post_render_pos = self.app_js.index("$('#gamesAfterMount')", show_result_pos)
        self.assertTrue(show_result_pos < show_view_pos < post_render_pos)

    def test_wizard_submit_is_guarded_against_double_click_re_entrancy(self):
        # Real bug found this round with a real (Playwright) mouse click,
        # not just a scripted .click(): #wizardNext's handler called
        # submitPrediction() directly with no re-entrancy guard, unlike
        # every other submit button on this page (auth forms already use
        # withSubmitLock - see the comment right above it). A slow
        # connection or an impatient double-click fired submitPrediction()
        # twice; each call creates its OWN processing overlay
        # (DWProcessing.run() appends a fresh element rather than reusing
        # one), so the second, still-in-flight overlay kept blocking every
        # click on the page - including the games view's own "See my
        # result" button - for its own full ~9s+ presentation window,
        # even after the first call had already rendered the games/result
        # view underneath it. Confirmed fixed with an actual Playwright
        # mouse click on #gamesContinueBtn after submission.
        next_btn_pos = self.app_js.index("wizardNextBtn.addEventListener('click'")
        # The handler must route the final-step submit through
        # withSubmitLock, not call submitPrediction() bare.
        handler_end = self.app_js.index("});", next_btn_pos)
        handler_body = self.app_js[next_btn_pos:handler_end]
        code_only = re.sub(r"//.*", "", handler_body)  # strip line comments before checking
        self.assertIn("withSubmitLock(wizardNextBtn, submitPrediction)", code_only)
        bare_calls = re.findall(r"(?<!withSubmitLock\(wizardNextBtn, )\bsubmitPrediction\(\)", code_only)
        self.assertEqual(
            bare_calls, [],
            "submitPrediction() must not be called directly from the wizard "
            "Next/Submit button - that reintroduces the double-submit bug.",
        )


if __name__ == "__main__":
    unittest.main()
