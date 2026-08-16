# Bug #1, fixed at the root: what the wellness score measures

The complaint was that screen time barely moved the score — a day of 658
screen minutes still scored 78. Two earlier attempts treated that as a
weighting problem and tuned coefficients. It was not a weighting problem.

## The actual root

`health_score_0_100` is **not a column in the dataset**. It is built in
`models/data_loader.py` from the six composite subscores the CSVs ship —
sleep, night use, focus, balance, stress/fatigue, activity. Every one of
them describes how a person slept and felt. **None of them measures how
long the screen was on.**

Measured on `data/train.csv`, the old score correlated:

| against | correlation |
|---|---|
| total screen minutes | **+0.105** |
| recreational minutes | **+0.034** |

Both nothing, and both the wrong sign. Grouped by recreational hours the
mean ran 62.5 (<2h), 65.0 (2–4h), 63.7 (4–6h), 61.6 (6–8h), 60.6 (8h+) —
a hump, not a decline, with the heaviest days landing within two points
of the lightest.

So no amount of re-weighting could have worked: there was no screen-load
term to weight.

## Why the first repair still could not agree with an outside reader

The first fix added a seventh subscore, but measured it against
`config/healthy_targets.py` — the app's own simulation table, which
allows 60 + 60 + 60 = 180 recreational minutes. That is internally
consistent and externally arbitrary. Three hours is half an hour past any
published guideline, so a score built on it could agree with itself and
with nothing else.

## What it measures now

`utils/screen_load.py`, with the sources cited in the module:

**Recreational volume.** Free to the **two-hour** recommendation, then a
logistic dose-response curve. Both of its parameters are *derived, not
chosen*: the literature says the rise is sharp between two and four
hours, so the midpoint is that band's centre (three hours) and the
steepness is set so the curve's own middle half spans exactly that band.
Nothing is left to pick. What falls out reads in whole fractions:

| recreational | 2 h | 3 h | 4 h | 5 h | 6 h |
|---|---|---|---|---|---|
| **subscore** | 100 | 67 | 33 | 13 | 5 |

**Pre-sleep use.** Its own risk, not a share of the daily total. Free to
**30 minutes** — the stricter of the two published cut-offs, since the
app cannot know whether the lights were on — fully charged at two hours.
These minutes are deliberately counted twice: the first term charges for
volume, this one for timing, and the same minute can be wrong on both.

**Work and study.** Every threshold in the research is about
*recreational* use, and the account model carries a `work_screen_required`
flag. Free to a full working day, gently charged past it, never able to
dominate.

Recreational volume is the spine — on its own it can take the subscore to
zero. The other two are charged on top.

A bug worth naming: the curve before this one was **concave where its own
docstring claimed convex** — its "shallow" segment was steeper per minute
than its "steep" one. `tests/ml/test_screen_load_subscore.py` now pins the
shape.

## The weight is a measurement, not a preference

It was 3/9, justified by "six terms outweigh three". Counting terms is the
wrong measure: the screen-load subscore has σ = 33.4 across the training
split against 7.9 for the mean of the six, so it outruns its share long
before its count does.

| weight | corr(score, recreational min) | corr(score, the six) |
|---|---|---|
| 1 | −0.518 | +0.818 |
| **2** | **−0.754** | **+0.577** |
| 3 | −0.844 | +0.425 |
| 4 | −0.883 | +0.331 |

At 3 the score is a screen-minute readout wearing a wellness score's name
— the original failure pointing the other way. **2** is the weight.

## The reported day

658.5 minutes: 269.5 recreational (4.5 h, more than twice the guideline)
and 389 work (inside a normal working day, so free). Screen load **21.7**,
and the day scores **65.2** where it scored 78.

## The classification half

`future_health_class_7d` is **real ground truth** — the one genuinely
forward-looking quantity in the data. Rebuilding it would mean inventing
labels and reporting accuracy against the invention, so it was measured
instead (`models/research_class_label_screen_response.py`, reproducing on
train *and* validation):

| the label responds to | |
|---|---|
| night_ratio | **−0.646** |
| pre_sleep_ratio | −0.512 |
| night_screen_min | −0.430 |
| total_screen_min | **+0.176** |
| recreational_min | **+0.106** |

The generator encoded screen **timing** as harmful and daytime **volume**
as roughly neutral, with the sign inverted. No feature engineering fixes
that — the signal is not in the target to be learned. The volume half of
the guidance therefore comes from the score, which measures it directly,
and never from the class.

### What that broke, and the fix

The seven-day estimator rests on one fact: *the class is a tertile band of
what it is calibrated against*, agreeing **80.2%** of the time. Once the
score carried two nearly independent axes (they correlate −0.006) and the
label banded only one of them, that fact failed — on the combined score
the agreement collapses to **43.3%**, against 33.3% by chance.

So the class → band reasoning now runs on the **wellbeing axis**, and the
screen-load half is **carried forward** from the user's own day:

```
score_7d = (6 · E[wellbeing_7d | class probs] + 2 · screen_load_today) / 8
```

Carried, not forecast. Nothing here predicts next week's screen time, and
leaving it as the user's own number makes it the part of the forecast they
can actually move.

`corr(today wellbeing, future wellbeing)` is **0.875**, identical to the
previous artifact's 0.875 — the forecasting construction is unchanged, it
was only being measured on the wrong axis.

## Four copies of one formula

The target is built in `data_loader.py`, and four other modules had each
written their own copy inline — `frame[SUBSCORES].mean(axis=1)`:

- `models/calibrate_future_score.py`
- `models/augment_future_score.py`
- `models/train_band_model.py`
- `services/ml/cohort_service.py`

Every copy was correct for exactly as long as the score *was* that mean.
The day it grew a seventh term, all four silently kept computing the old
one, with nothing failing anywhere. The app would have shown a
screen-aware score for today beside a screen-blind band for next week and
a screen-blind cohort percentile underneath.

Two of them documented themselves as safe: `train_band_model` called the
duplication a deliberate saving, and `cohort_service`'s docstring claimed
the formula was "imported from there rather than re-implemented" on the
line directly above the re-implementation.

All four now call `reconstruct_health_score`.
`tests/ml/test_one_score_definition.py` parses each module's AST and fails
if a fifth copy appears — a comment saying so was not enough twice.

## Consequences found by checking rather than assuming

- **`corr(today, target)` rose to 0.954**, above the 0.939 that got an
  earlier approach rejected. Not the same thing: two thirds of the new
  target's variance is the carried screen-load half, so the figure is high
  by construction. Both numbers are now in the artifact, with the
  wellbeing-axis one marked as the one that carries the claim.
- **The two-stage estimator's margin fell from 55.33% to 22.19%** over the
  predict-today baseline. That baseline is far stronger than it was, for
  the same reason. It still clears the 15% gate.
- **`HEALTHY_TARGETS` contradicted the score** — reaching all three
  targets (180 min) would have said "you have arrived" while the score
  took a third of the digital-load points off. Now sums to the guideline.
  The work target said 240 while calling itself "a normal working day";
  now 480, matching what the score charges.
- **The borderline demo profile fell out of its own band.** 310
  recreational minutes scored 48.2 — inside at-risk (0–49) — while the
  demo went on calling it borderline and showing it as moderate. Now 180
  minutes, scoring 56.2.
- **The regressor's R² rose 0.974 → 0.981 while MAE also rose 0.83 →
  0.99.** That is not the model improving: the target's σ went 7.9 → 10.2,
  so the same fit buys more R². Some of the rest is mechanical, since
  screen load is arithmetic on four fields that are themselves features.
- **The estimator briefly hard-required the new argument.** Making
  `screen_load_today` mandatory meant every caller that omitted it
  dropped through to the class-typical path and got that class's mean
  back — a user on 70 and a user on 95 were both told 72.2. Caught by
  four existing tests that pin the product properties ("stay in your
  band, keep your own number"; "no ceiling"). It now falls back to
  reading the position off the score and applying the band move at full
  weight, which is exactly what it did before the score had two axes, so
  the new code is a strict generalisation rather than a new requirement.

## One test was changed, and why

`test_the_target_is_not_just_todays_score` asserted
`corr_with_today < 0.95` and began failing at 0.954. The intent is right
and the subject went stale: that correlation is taken on the combined
score, two thirds of whose variance is the carried screen-load half, so
it is high by construction and would be high even if the forecast were
worthless.

It now asserts on `corr_wellbeing_with_today` — the axis something is
actually predicted on — which is **0.875**, unchanged. A second test was
added rather than simply relaxing the threshold, because relaxing a
threshold when a number goes up is how a real regression gets waved
through: it requires the artifact to show that the gap between the two
correlations really is the carried half (share between 0.5 and 0.9, and
the combined figure still short of a pure echo).

## Retrained

`train_regression` → `calibrate_future_score` → `augment_future_score` →
`train_future_regression` → `train_band_model`.

The **classifier was not retrained and did not need to be**: its target is
unchanged and `screen_load_subscore` is excluded from its feature set as a
component of the other target.

| model | metric | result |
|---|---|---|
| Wellness score, today | MAE / RMSE / R² (test) | 0.99 / 1.35 / 0.981 |
| Seven-day estimator (two-stage) | MAE vs predict-today | 22.19% better, gate 15% |
| Weekly band half-width | coverage @ 0.90 (test) | 0.893 |
