# The personal weekly band

*How the weekly plan's score range stopped being a constant.*

---

## 1. The problem, with a number attached

The weekly plan is aimed at a **range**, not a single target. Until now that range was:

```
weighted mean of this week's logged scores  ±  6.0
```

The `6.0` was hand-picked. Measured against the dataset's real per-respondent
day sequences, replaying exactly what the live app does — reset every seven
days, compare each day against the running mean of the days before it — it is
wrong in two independent ways.

**It is too wide.**

| Half-width | Coverage | A day falls outside it |
|---|---|---|
| 6.0 (shipped) | 98.2% | once every **78 days** |

The band exists to trigger one question: *"that day was outside your range —
was it unusual, or a real change?"* That question has its own UI, its own
`EXCEPTION_WEIGHT = 0.25` machinery, its own violation interaction and four
languages of copy. At 98.2% coverage it was being asked roughly **once every
eleven weeks**.

**It is the same for everybody.** The half-width each respondent actually
needs for 90% coverage:

| p10 | median | p90 | max |
|---|---|---|---|
| 2.70 | 3.73 | 5.14 | 8.19 |

A **1.9×** spread between the calmest and the most volatile tenth. 19% of
respondents need less than half of 6.0.

---

## 2. What was built

Only the **width** changed. The centre is still the weighted mean of the days
logged this week, the exception weight still moves that centre and nothing
else, the ISO-week lock still freezes the whole thing, and every other weekly
plan rule — focus selection, tiers, day unlocking, violations — is untouched.

**Conformalized Quantile Regression** (Romano, Patterson & Candès, 2019), the
same uncertainty family the shipped score model already uses:

1. A `HistGradientBoostingRegressor` with the **pinball loss at q = 0.90**
   predicts, from a user's week so far, the quantile of
   `|next day − running mean|`. That is the raw half-width.
2. A **group-disjoint calibration set** turns that into a guarantee. The
   conformity score is `actual deviation − predicted half-width`; its ceiling
   quantile (with the finite-sample `(n+1)/n` correction) is added to every
   prediction. Marginal coverage ≥ 0.90 then holds distribution-free, without
   assuming the regressor is any good.

Step 2 is why this is worth shipping over a plain quantile model: a badly
calibrated regressor gets absorbed by the correction, and the band stays
honest — only wider.

### Where the rows come from

Exactly the way the live app computes a band, and no other way:

- respondents recovered by the same ten-column key `models/regenerate_user_split.py`
  uses; groups with a repeated `day_index` are **dropped**, because a repeat is
  the fingerprint of that key merging two people, and merged days cannot be ordered;
- each sequence cut into **7-day blocks**, because the live band resets with the
  ISO week and never sees more than seven days;
- within a block, every prefix of length *t* (1 ≤ *t* ≤ 6) is one row: features
  from days 1..*t*, target `|day t+1 − mean(1..t)|`.

| | respondents | rows |
|---|---|---|
| fit | 753 | 14,307 |
| conformal calibration | 323 | 6,137 |
| validation | 77 | 1,463 |
| **test (held out by respondent)** | **69** | **1,311** |

---

## 3. The features

25 columns, defined once in `utils/band_features.py` and imported by **both**
the trainer and the service — the same discipline `utils/feature_derivation.py`
enforces for the shipped models.

**13 sequence features** — `n_days`, running mean, SD, mean absolute deviation,
range, last-day deviation, OLS slope, mean and max day-to-day change,
EWMA volatility (α = 0.5), last/min/max.

**12 habit features** — 10 fields from the latest logged day
(`sleep_hours`, `sleep_quality_1_10`, `total_screen_min`, `night_ratio`,
`social_ratio`, `stress_0_10`, `focus_0_100`, `fragmentation_index_0_100`,
`pickups_per_day`, `physical_activity_min_per_day`), plus the week's SD of
`sleep_hours` and `total_screen_min`. Every one of them is in
`history_service.TRACKED_FIELDS`, so training reads out of the dataset exactly
the field the app stores per entry.

**Missing means missing.** Absent habit fields and the dispersion of a single
day are emitted as **NaN**, not zero — `HistGradientBoosting` handles NaN
natively. Zero-filling would make a user with no stored sleep figure look like
a user who slept zero hours.

---

## 4. Results, held out by respondent

Target coverage **0.90**. Conformal offset **+0.098**.

| | coverage | mean half-width | width p10–p90 |
|---|---|---|---|
| shipped constant 6.0 | 0.980 | 6.00 | 6.00 – 6.00 |
| **best possible constant** (4.25) | 0.902 | 4.25 | 4.25 – 4.25 |
| **this model** | **0.896** | **4.11** | **3.36 – 4.85** |

The "best possible constant" is the strong baseline: the empirical quantile of
the same calibration days the model's offset came from. Beating 6.0 is trivial;
beating this is what proves personalisation earns its place.

### The argument, in one table

Bucket respondents by how much they actually move, then check coverage
*inside* each bucket. A constant hits its average by over-covering calm people
and under-covering volatile ones — and only this view shows it.

| volatility tercile | constant 6.0 | best constant | **this model** |
|---|---|---|---|
| calm | 1.000 (w 6.00) | 0.970 (w 4.25) | 0.943 (w **3.79**) |
| middle | 0.988 (w 6.00) | 0.914 (w 4.25) | 0.907 (w **4.12**) |
| **volatile** | 0.953 (w 6.00) | **0.823** (w 4.25) | **0.839** (w **4.41**) |
| worst-tercile gap vs target | −0.053 | **+0.077** | **+0.062** |

The width column is the point: a constant reports the same number three times;
the model widens 3.79 → 4.41 as people get more volatile, and narrows the
unfairness from +0.077 to +0.062 at a *smaller* average width (4.11 against
4.25). The margin is thinner than it was before the training split was
de-contaminated — the earlier +0.037 was measured against a test set that
shared 88% of its rows with train.

### Ablation: which block earns its place?

Three nested feature sets, each refitted and conformalised identically on
**every training run** rather than quoted from memory, and written into
`artifacts/metrics_band.json`. Nested rather than run separately, so each step
is attributable to one block:

| | coverage | mean width | worst-tercile gap |
|---|---|---|---|
| sequence only | 0.899 | 4.15 | +0.068 |
| **+ the person's earlier weeks** | 0.897 | 4.13 | **+0.058** |
| + habit fields (shipped) | 0.896 | 4.11 | +0.062 |

Knowing a user's own prior weeks is what closes the fairness gap: +0.068 →
+0.058, a 15% reduction, and it also narrows the band. The sleep/screen/stress
fields on top buy a slightly tighter average width and give **0.004 of the gap
back** — they are shipped because they still beat the sequence-only model and
the best constant on both gates, but the honest reading is that the
prior-history block is doing the work here, not the habit block. That is a
change from the pre-decontamination measurement, where the habit fields
appeared to halve the gap.

`tests/ml/test_personal_band_model.py` fails if either the prior block or the
full set stops beating sequence-only.

---

## 5. The honesty gate

`models/train_band_model.py` **refuses to write the artifact** unless both hold
on the held-out respondents:

1. marginal coverage within 2pp of target;
2. worst volatility tercile fairer than the best constant.

Same rule that kept `models/train_future_regression.py`'s output out of
production. An artifact on disk with `beats_baseline: false` would mean someone
put it there by hand — and `tests/ml/test_personal_band_model.py` checks for that.

---

## 6. Failing safe

`services/ml/band_model_service.half_width()` returns `None` on **any** problem,
and `week_band()` reads `None` as "use `BAND_HALF_WIDTH`". No artifact, a pickle
that will not load, a prediction that raises, a user with no usable day — all of
them land back on the constant. Nobody loses their weekly plan because a model
file is missing.

It also **refuses a model it does not understand**: `feature_columns_band.json`
is compared against `utils/band_features.BAND_FEATURE_COLUMNS` before the
artifact is accepted. Add a feature and forget to retrain, and every position
past the insertion point silently means something else — the model would answer
anyway, with a number that looks completely reasonable. That is refused, not
tolerated.

The API reports `band_source` (`model` | `constant` | `explicit`) and
`band_half_width` alongside the edges, for the same reason the cohort panel
names its source: a reader is entitled to know whether the range in front of
them was fitted to them or is the one everybody gets.

---

## 7. What this does **not** claim

- **The data is synthetic.** Coverage is measured on held-out *respondents*,
  not held-out days of the same people, which is the right split — but it says
  the band is calibrated on this dataset, not that it describes human behaviour.
- **Volatile users are still under-covered**: 0.863 against a 0.90 target. That
  is better than the best constant's 0.808 and it is not 0.90. Closing it
  properly needs conditional (Mondrian) conformal calibration per volatility
  bucket, which needs more respondents than 1,076 usable sequences supply.
- **69 held-out respondents** is a small test set. The validation split (77
  respondents) agrees closely — 0.908 coverage, +0.040 worst-tercile gap — which
  is the only reason the test figure is quoted at all.

---

## Reproduce

```bash
python3 -m models.train_band_model          # writes artifacts/band_model.pkl + metrics_band.json
python3 -m unittest tests.test_personal_band_model
```

| File | What it is |
|---|---|
| `utils/band_features.py` | the 25 features, shared by both sides |
| `models/train_band_model.py` | fitting, conformal calibration, the gate, the ablation |
| `services/ml/band_model_service.py` | inference, and every way it declines to answer |
| `services/wellness/plan_lock_service.py` | `week_band` / `week_band_detail` — the rule itself |
| `artifacts/metrics_band.json` | every number on this page |
| `tests/ml/test_personal_band_model.py` | 35 tests |
