"""There is one definition of `health_score_0_100`, and it is imported.

The defect this exists for. The target is not a raw column - it is built
in models/data_loader.py. Four other modules had each written their own
copy of the formula inline:

  * models/calibrate_future_score.py
  * models/augment_future_score.py
  * models/train_band_model.py
  * services/ml/cohort_service.py

Every copy was `frame[SUBSCORES].mean(axis=1)`, and every copy was
correct for exactly as long as the score WAS that mean. The day it grew
a seventh screen-load term, all four silently went on computing the old
one. Nothing failed. The app would have shown a screen-aware score for
today beside a screen-blind band for next week and a screen-blind cohort
percentile underneath, with no error anywhere.

Two of the copies even documented themselves as safe: train_band_model
called the duplication a deliberate saving, and cohort_service's
docstring claimed the formula was "imported from there rather than
re-implemented" on the line above the re-implementation.

So this does not test arithmetic. It tests that the arithmetic lives in
one place, because a comment saying so was not enough twice.
"""

from __future__ import annotations

import ast
import unittest

from core import paths

# Modules that need the target and must import it rather than rebuild it.
CONSUMERS = (
    "models/calibrate_future_score.py",
    "models/augment_future_score.py",
    "models/train_band_model.py",
    "services/ml/cohort_service.py",
)

OWNER = "models/data_loader.py"


def _source(relative: str) -> str:
    path = paths.PROJECT_ROOT / relative
    if not path.exists():
        raise unittest.SkipTest(f"{relative} is not present")
    return path.read_text(encoding="utf-8")


def _mean_over_subscores(tree: ast.AST) -> list[int]:
    """Line numbers of any `<something subscore-ish>.mean(axis=...)` call.

    Deliberately structural rather than a text search: a copy that
    renamed its local list, or reformatted across lines, is the same bug
    and would slip past a grep for one exact string.
    """
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "mean"):
            continue
        if not any(kw.arg == "axis" for kw in node.keywords):
            continue
        # Subscript of a name containing "SUBSCORE" - the shape every
        # one of the four copies had.
        target = func.value
        if isinstance(target, ast.Subscript):
            index = target.slice
            name = getattr(index, "id", None)
            if name and "SUBSCORE" in name.upper():
                hits.append(node.lineno)
    return hits


class TestOnlyTheLoaderBuildsTheTarget(unittest.TestCase):
    def test_no_consumer_recomputes_the_mean_of_the_subscores(self):
        for relative in CONSUMERS:
            with self.subTest(module=relative):
                hits = _mean_over_subscores(ast.parse(_source(relative)))
                self.assertEqual(
                    hits, [],
                    f"{relative} rebuilds the target inline at line(s) {hits}. "
                    "Import models.data_loader.reconstruct_health_score instead - "
                    "it is the cheap half of the loader and does no "
                    "derived-feature rebuild.",
                )

    def test_every_consumer_imports_the_one_definition(self):
        for relative in CONSUMERS:
            with self.subTest(module=relative):
                self.assertIn(
                    "reconstruct_health_score", _source(relative),
                    f"{relative} needs the target but never imports it",
                )

    def test_the_loader_still_owns_it(self):
        source = _source(OWNER)
        self.assertIn("def reconstruct_health_score(", source)
        # Public, not underscore-private: four modules have to be able
        # to import it, which is the whole point.
        self.assertNotIn("def _reconstruct_health_score(", source)


class TestTheDefinitionIsTheOneTheModelsWereFitOn(unittest.TestCase):
    def test_it_carries_the_screen_load_term(self):
        from models.data_loader import (
            SCREEN_LOAD_COLUMN, SCREEN_LOAD_WEIGHT, SUBSCORE_COLUMNS,
            WELLBEING_COLUMN, reconstruct_health_score,
        )
        import pandas as pd

        row = {column: 60.0 for column in SUBSCORE_COLUMNS}
        row.update(social_min=600.0, gaming_min=0.0, video_min=0.0,
                   other_min=0.0, work_study_min=0.0, pre_sleep_screen_min=0.0)
        frame = reconstruct_health_score(pd.DataFrame([row]))

        # Ten recreational hours: the screen-load term is spent, so the
        # score must sit well below the flat 60 the six subscores give.
        self.assertLess(frame[SCREEN_LOAD_COLUMN].iloc[0], 1.0)
        self.assertAlmostEqual(frame[WELLBEING_COLUMN].iloc[0], 60.0, places=6)
        expected = (60.0 * len(SUBSCORE_COLUMNS)) / (len(SUBSCORE_COLUMNS) + SCREEN_LOAD_WEIGHT)
        self.assertAlmostEqual(frame["health_score_0_100"].iloc[0], expected, delta=0.5)

    def test_it_leaves_an_existing_target_alone(self):
        import pandas as pd
        from models.data_loader import reconstruct_health_score

        frame = pd.DataFrame([{"health_score_0_100": 42.0}])
        self.assertEqual(
            reconstruct_health_score(frame)["health_score_0_100"].iloc[0], 42.0)


if __name__ == "__main__":
    unittest.main()
