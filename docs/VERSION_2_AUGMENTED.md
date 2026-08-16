# Version 2 — a seven-day number, built by data augmentation

This build shows a **score for today**, a **class for seven days from
now**, and a **score for seven days from now**. The third one does not
come from a model trained on a real seven-day target, because no such
target exists in this dataset. It comes from augmenting the target that
does exist, and it beats the only honest baseline by a wide margin.

---

## What you see in the app

| figure | source | horizon | shown as |
|---|---|---|---|
| today's score | regression model | **today** | bold 0–100 in the middle of the ring, with its band |
| seven-day class | classification model | **7 days ahead** | `At Risk` / `Moderate` / `Healthy` + confidence |
| seven-day score | two-stage estimator | **7 days ahead** | a number with an 80% interval, labelled `augmented_rank` |

## How the number is built

The finding that makes this possible: the seven-day class **is** the
tertile band of the **wellbeing** half of the score — the mean of the six
composite subscores. They agree on 80.2% of rows, and the class means sit
within 0.6 points of the tertile means. So the classifier already tells
you which third of the range someone lands in seven days from now — it
just does not tell you where inside that third.

**The wellbeing half, specifically.** The score also carries a
screen-load term, and the two halves correlate −0.006 with each other.
Against the *combined* score the class agrees with its own tertiles only
43.3% of the time — against 33.3% by chance — so the finding above is
true on one axis and false on the other. The bands, the quantile tables
and the rank persistence are therefore all on the wellbeing axis, and the
estimate is put back on the score's scale by carrying the user's own
screen load for the day forward unchanged. Carried, not forecast: nothing
here predicts next week's screen time, and leaving it as the user's own
number makes it the part of the forecast they can actually move.

The augmentation supplies the missing half by **within-band rank
persistence**: someone in the 70th percentile of their band today is
assumed to be near the 70th percentile of their predicted band next
week. Both "bands" are the same three tertile slices of the score
distribution, and the estimate is applied as a **shift on the user's own
score**, so a user the classifier keeps in their current band gets their
current score back. An earlier version read the position off the spread
of today's scores *within a class* instead, which capped every user
above 78.67 — the highest scorer in the data was told to expect a fall. `models/augment_future_score.py` writes the band edges, the
today-band cuts and 101 quantile points per band into
`artifacts/future_score_augmentation.json`.

At prediction time the two stages are:

1. the shipped classifier picks the band,
2. the user's own within-band position today picks the place inside it.

No third model is trained. The interval is the mixture variance across
the classifier's class probabilities (law of total variance) **plus the
estimator's own error in quadrature** — without that second term a
confident classifier produced a ±0.1-point range, which is a precision
claim nothing here can support.

## What was rejected, and why it stays on the record

**Global rank persistence** — assuming your percentile across the whole
population persists — was tried first and rejected on measurement: it
produced a target correlated **0.939** with today's score. A model fitted
to that would be predicting today and calling it next week. The rejection
is stored in the artifact (`rejected_alternative`) and asserted by a test,
so it cannot quietly come back.

**A single-stage regressor** was trained on the augmented target and
lost:

| estimator | validation MAE | validation R² | vs. "predict today unchanged" |
|---|---|---|---|
| baseline: predict today unchanged | 1.70 | 0.7802 | — |
| single-stage regressor | 2.98 | 0.7695 | **75.17% worse** |
| **two-stage estimator (shipped)** | **1.41** | **0.9078** | **17.21% better** |

The baseline is *harder* than it looks. Because the target now keeps a
user's score when their band does not change, "predict today unchanged"
is already a good answer for the ~80% of rows whose band is stable —
which is why the margin here is 17% and not the 55% an earlier, more
compressed version of the target reported. The gate was set at 15%
before any of these numbers existed.

The acceptance gate was set at 15% before the numbers were in. The
single-stage attempt is kept in `artifacts/metrics_future_regression.json`
rather than deleted — a metrics file that shows only the winner hides
why the winner won.

## The honest caveat, stated in the artifact and in the app

That R² is measured against a **constructed** target. It is not a
measurement of how accurately anyone's real score seven days from now is
predicted, and the underlying dataset is synthetic to begin with. The
artifact carries this sentence in `honest_description`, and a test
asserts the word `CONSTRUCTED` is present.

## Accuracy in this build

| model | metric | validation | test |
|---|---|---|---|
| classifier (7-day class) | accuracy | **90.34%** | **97.69%** |
| classifier | ROC-AUC | 98.46% | 99.82% |
| regressor (today's score) | R² | **95.68%** | **99.17%** |
| regressor | MAE | 1.25 points | 0.50 points |
| two-stage 7-day estimator | R² | **90.78%** | 97.33% |
| two-stage 7-day estimator | MAE | 1.41 points | 0.63 points |

## Running it

```bash
pip install -r requirements.txt
python run.py            # Windows: double-click start.bat
```

`run.py` starts the API (which serves the web pages itself) and opens
your browser. Do **not** serve the `frontend/` folder with a separate
static server — it shows the pages but cannot answer a sign-in, and you
get `501 Unsupported method ('POST')` on the login button.

`augmented` is the built-in default. To see what Version 1 does without
switching builds:

```bash
DWAI_FUTURE_SCORE_MODE=class_only uvicorn api.main:app
```

To rebuild the augmented target and re-run the comparison:

```bash
python3 -m models.augment_future_score
python3 -m models.train_future_regression
```
