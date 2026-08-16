"""The simulator picks its starting day, and can start from history.

Two defects this pins.

The page was pinned to `dwai_last_payload`, a value only this browser's
own last check-in writes. There was no way to ask "what if, on that heavy
Saturday" from a Tuesday, and an account with fifteen recorded days
opened on a second device was told there was nothing to simulate - which
was never true, because /history/snapshots had every one of those days'
answers all along.

The day list, the field's value on the chosen day, and the percentage
target are all read from that response, so what the simulator runs
against is a day the user actually recorded rather than whatever the
browser happened to keep.
"""

from __future__ import annotations

import re
import unittest

from core import paths

PAGE = paths.PROJECT_ROOT / "frontend/whatif.html"
SCRIPT = paths.PROJECT_ROOT / "frontend/assets/js/pages/whatif.js"
I18N = paths.PROJECT_ROOT / "frontend/assets/js/core/i18n.js"

NEW_KEYS = (
    "whatif_day_title",
    "whatif_day_sub",
    "whatif_field_now",
    "whatif_field_target_pct",
    "whatif_field_target_value",
)


class TestTheMarkupOffersTheChoice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")

    def test_the_day_picker_exists(self):
        self.assertIn('id="whatifDay"', self.page)

    def test_the_field_target_controls_exist(self):
        for element in ("fieldNow", "fieldTargetPct", "fieldTargetValue"):
            with self.subTest(element=element):
                self.assertIn(f'id="{element}"', self.page)

    def test_the_two_readouts_are_not_editable(self):
        # They are derived from the chosen day and the percentage; typing
        # into them would show a number the simulation is not using.
        for element in ("fieldNow", "fieldTargetValue"):
            with self.subTest(element=element):
                block = re.search(
                    r'<input[^>]*id="' + element + r'"[^>]*>', self.page
                )
                self.assertIsNotNone(block, f"{element} input not found")
                self.assertIn("readonly", block.group(0))

    def test_the_percentage_input_is_bounded(self):
        block = re.search(r'<input[^>]*id="fieldTargetPct"[^>]*>', self.page)
        self.assertIsNotNone(block)
        self.assertIn('min="0"', block.group(0))
        self.assertIn("max=", block.group(0))


class TestItReadsRealRecordedDays(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text(encoding="utf-8")

    def test_the_days_come_from_the_history_endpoint(self):
        self.assertIn("historySnapshots(", self.script)

    def test_history_is_fetched_once_and_reused(self):
        # The picker used to call it a second time. Two calls for one
        # list is a wasted round trip and a chance for the two to
        # disagree.
        self.assertEqual(self.script.count("historySnapshots("), 1)

    def test_an_account_with_history_is_never_told_it_has_nothing(self):
        empty_gate = self.script.index("whatifEmpty")
        fallback = self.script.index("historySnapshots(")
        self.assertLess(
            fallback, empty_gate,
            "the empty state is decided before history is consulted",
        )

    def test_choosing_a_day_replaces_what_the_simulation_runs_on(self):
        self.assertIn("payload = entry.inputs", self.script)

    def test_the_target_value_is_derived_from_the_chosen_day(self):
        self.assertIn("now * (pct / 100)", self.script)


class TestTheNewStringsAreTranslated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.i18n = I18N.read_text(encoding="utf-8")

    def test_every_new_key_exists_in_all_four_languages(self):
        for key in NEW_KEYS:
            with self.subTest(key=key):
                self.assertEqual(
                    self.i18n.count(f"{key}:"), 4,
                    f"{key} is not present once per language",
                )


if __name__ == "__main__":
    unittest.main()
