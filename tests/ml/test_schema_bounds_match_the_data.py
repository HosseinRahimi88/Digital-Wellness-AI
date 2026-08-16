"""No FEATURE_SCHEMA bound may reject a day the models were fitted on.

The defect: the three per-hour densities are computed by dividing a daily
count by hours of screen time, so a short screen day divides by a small
number - 200 notifications across 12 minutes of screen is 1000 per hour,
which is arithmetic, not a typo. All three carried a ceiling of 100.
Measured on the validation split, 87 rows exceeded it for
notification_density (max 1127.2) and 28 for pickup_density (max 168.0).

Those rows are in the data the shipped models were trained against, so
the validator was refusing days the model had already learned from. It
also cost the what-if simulator most of its sweep: driving social_min
down shrinks screen time, the density climbs past the ceiling, and the
points came back as gaps - which is how goal_seek ended up reporting a
"best value" of 780 minutes.
"""

from __future__ import annotations

import unittest

import pandas as pd

from core.feature_schema import FEATURE_SCHEMA
from core import paths
from models.data_loader import reconstruct_derived_features


class TestEveryBoundAdmitsTheTrainingData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The validation split rather than train: same distribution, a
        # twentieth of the parse time.
        cls.frame = reconstruct_derived_features(
            pd.read_csv(paths.PROJECT_ROOT / "data" / "validation.csv")
        )

    def test_no_column_falls_outside_its_own_schema_bounds(self):
        offenders = []
        for name, feature in FEATURE_SCHEMA.items():
            if name not in self.frame.columns:
                continue
            column = self.frame[name].dropna()
            if column.empty or not pd.api.types.is_numeric_dtype(column):
                continue
            if feature.maximum is not None and (column > feature.maximum).any():
                offenders.append(
                    f"{name}: {int((column > feature.maximum).sum())} rows above "
                    f"maximum {feature.maximum} (observed max {column.max():.2f})"
                )
            if feature.minimum is not None and (column < feature.minimum).any():
                offenders.append(
                    f"{name}: {int((column < feature.minimum).sum())} rows below "
                    f"minimum {feature.minimum} (observed min {column.min():.2f})"
                )
        self.assertEqual(
            offenders, [],
            "FEATURE_SCHEMA would reject days the models were fitted on:\n  "
            + "\n  ".join(offenders),
        )

    def test_the_densities_keep_headroom_over_what_was_observed(self):
        # Not merely "above the maximum seen": a real user can be more
        # extreme than any synthetic row, and a bound set flush against
        # the data would start rejecting them.
        for name in ("notification_density", "pickup_density"):
            with self.subTest(field=name):
                observed = self.frame[name].dropna().max()
                self.assertGreater(FEATURE_SCHEMA[name].maximum, observed * 1.2)


if __name__ == "__main__":
    unittest.main()
