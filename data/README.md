# data/

The training corpus. **The application does not read anything in this
folder** — it serves predictions from the fitted models in `artifacts/`.
These files are only needed to retrain.

## The three splits

| File | Rows | Purpose |
|---|---|---|
| `train.csv` | 80,312 | Model fitting |
| `validation.csv` | 5,022 | Model selection, and the conformal calibration set |
| `test.csv` | 5,017 | Touched once, at the end, for the reported numbers |

70 columns: the raw daily signals, the derived features rebuilt by
`models/data_loader.reconstruct_derived_features`, both targets
(`health_score_0_100`, `future_health_class_7d`), and the bookkeeping
columns that are excluded from every feature set
(`models/preprocessing.get_feature_columns`).

## How the split is made

Not randomly. `models/regenerate_user_split.py` pools all three files,
canonicalises them through a CSV round-trip, drops exact duplicate rows,
and re-splits with `StratifiedGroupKFold` grouped on a ten-column
demographic signature, so no respondent's rows can land on both sides of
a boundary.

The round-trip before the dedup matters: pandas' default float
formatting is not fully round-trippable, so two rows that are identical
*in the file* can differ in memory. Deduplicating the in-memory frame
leaves the duplicates in place on disk. Deduplicating the canonicalised
frame does not.

Regenerate with:

```bash
python -m models.regenerate_user_split
```

It archives whatever it is about to overwrite into
`data/archive_pre_user_split_fix/` first. After regenerating, every model
must be refitted — the artifacts in `artifacts/` were fitted against the
previous files and their metrics no longer describe the new ones.

## Provenance

Synthetic. The generator wrote each respondent's trajectory against a day
counter, which is why `day_index` and any cumulative counter are excluded
from the feature set — they predict the target well and mean nothing for
a real person. The measurement is in
`models/research_classification_trend.py`.
