"""A model and its feature-column list have to be the same pair.

The defect this exists for, in the shape it actually arrived in.

`artifacts/health_classifier.pkl` and `artifacts/feature_columns.json`
are written together by models/train_classification.py and are meaningless
apart. Nothing checked that the two on disk belonged to each other -
ModelRegistry.validate() confirmed both files EXISTED and stopped there.

A merge then took the model from one tree and the column list from
another. Both files were present, both were valid, and the app started
and answered /health as "ok". What it could not do was score a single
day: the classifier had been fitted on 184 columns and the list beside it
named 52.

The first complaint came from several frames below anything in this
repository - inside sklearn's ColumnTransformer, during split-conformal
calibration - as `ValueError: columns are missing: {...}` printing 133
feature names. Nothing in that pointed at a stale JSON file. It cost a
CI run and a debugging session to trace back.

So the pairing is checked where both are loaded, and a mismatch is
refused with the two counts and a sample of the difference.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from core import paths
from models.model_registry import ModelRegistry

ARTIFACTS = paths.ARTIFACTS_DIR


def _registry_pointed_at(directory: Path, task: str) -> ModelRegistry:
    """A registry reading `directory` instead of artifacts/.

    The paths are computed in __init__ from a fixed root, so they are
    repointed afterwards rather than by constructor argument - which
    keeps this test from requiring a production code change that exists
    only for testing.
    """
    registry = ModelRegistry(task=task)
    names = {
        "classification": ("health_classifier.pkl", "feature_columns.json",
                           "metrics.json", "model_info.json"),
        "regression": ("health_regressor.pkl", "feature_columns_regression.json",
                       "metrics_regression.json", "model_info_regression.json"),
    }[task]
    registry.artifacts_dir = directory
    registry.model_path = directory / names[0]
    registry.feature_columns_path = directory / names[1]
    registry.metrics_path = directory / names[2]
    registry.model_info_path = directory / names[3]
    return registry


class TheShippedArtifactsAgree(unittest.TestCase):
    """The check that would have caught it, run against what ships."""

    def test_every_task_validates(self):
        for task in ("classification", "regression"):
            with self.subTest(task=task):
                self.assertTrue(ModelRegistry(task=task).validate())

    def test_the_column_list_is_exactly_what_the_model_was_fitted_on(self):
        for task, filename in (
            ("classification", "feature_columns.json"),
            ("regression", "feature_columns_regression.json"),
        ):
            with self.subTest(task=task):
                registry = ModelRegistry(task=task)
                model = registry.model
                expected = getattr(model, "feature_names_in_", None)
                if expected is None and getattr(model, "steps", None):
                    expected = getattr(model.steps[0][1], "feature_names_in_", None)
                if expected is None:
                    self.skipTest(f"{task} model records no input schema")
                self.assertEqual(
                    list(registry.feature_columns), list(expected),
                    f"artifacts/{filename} is not the list "
                    f"{registry.model_path.name} was fitted on",
                )


class AMismatchedPairIsRefused(unittest.TestCase):
    def setUp(self):
        for name in ("health_classifier.pkl", "feature_columns.json",
                     "metrics.json", "model_info.json"):
            if not (ARTIFACTS / name).exists():
                self.skipTest(f"artifacts/{name} is not present")
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory, True)
        for name in ("health_classifier.pkl", "feature_columns.json",
                     "metrics.json", "model_info.json"):
            shutil.copy(ARTIFACTS / name, self.directory / name)
        self.columns = self.directory / "feature_columns.json"

    def _validate(self):
        return _registry_pointed_at(self.directory, "classification").validate()

    def test_the_untouched_copy_still_validates(self):
        # Guards the guard: if this failed, the failures below would
        # prove nothing about mismatches.
        self.assertTrue(self._validate())

    def test_a_truncated_list_is_caught(self):
        # The exact shape of the real defect: the model keeps its 184
        # columns, the list beside it is an older, shorter one.
        full = json.loads(self.columns.read_text(encoding="utf-8"))
        self.columns.write_text(json.dumps(full[:52]), encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            self._validate()
        message = str(caught.exception)
        self.assertIn("does not match the model", message)
        self.assertIn(str(len(full)), message)
        self.assertIn("52", message)

    def test_the_message_names_the_columns_that_went_missing(self):
        full = json.loads(self.columns.read_text(encoding="utf-8"))
        self.columns.write_text(json.dumps(full[:-3]), encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            self._validate()
        # A reader has to be able to tell WHICH artifact is stale without
        # loading either of them; the raw sklearn error named 133
        # columns and neither file.
        self.assertIn("feature_columns.json", str(caught.exception))
        self.assertIn("health_classifier.pkl", str(caught.exception))

    def test_an_extra_unknown_column_is_caught(self):
        full = json.loads(self.columns.read_text(encoding="utf-8"))
        self.columns.write_text(
            json.dumps(full + ["a_column_the_model_never_saw"]), encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            self._validate()
        self.assertIn("a_column_the_model_never_saw", str(caught.exception))

    def test_reordering_alone_is_caught(self):
        # sklearn matches a ColumnTransformer's columns by position as
        # well as by name, so the same names in a different order is a
        # real mismatch and not a cosmetic one.
        full = json.loads(self.columns.read_text(encoding="utf-8"))
        self.columns.write_text(
            json.dumps(full[1:] + full[:1]), encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            self._validate()
        self.assertIn("same names, different order", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
