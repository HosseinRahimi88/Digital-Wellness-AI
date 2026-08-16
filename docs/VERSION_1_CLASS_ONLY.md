# Version 1 — the seven-day future is a class, and only a class

This build takes the honest way out of a problem the dataset cannot
solve. It shows a **score for today** and a **class for seven days from
now**, and it refuses to show a seven-day score at all.

That refusal is the feature. Everything below is why.

---

## What you see in the app

| figure | model | horizon | shown as |
|---|---|---|---|
| today's score | regression | **today** | a bold 0–100 number in the middle of the ring, with its band |
| seven-day class | classification | **7 days ahead** | `At Risk` / `Moderate` / `Healthy`, with the classifier's confidence |
| seven-day score | — | — | **not shown; there is no number to show** |

`services/insight/future_score_service.py` runs in `class_only` mode. In that
mode `estimate()` returns `available = False` with `basis =
"class_only"` and `score = None`. The point is that there **is** no
number, not that one was computed and hidden — a test asserts exactly
that (`test_class_only_mode_returns_no_number_at_all`).

## Why there is no seven-day score

The dataset has no user id and no date, its rows are shuffled, and the
only usable cohort key over-groups 73% of rows into one bucket. Pairing
rows to reconstruct "the same person seven days later" yields a subset
that is 99.3% one class. So a genuine seven-day-ahead score target
cannot be recovered from this data.

A regressor was still trained against a reconstructed target to test
that conclusion rather than assert it. It is kept in the record because
the result is the finding:

| estimator | validation MAE | vs. "predict today unchanged" |
|---|---|---|
| baseline: predict today unchanged | 3.31 | — |
| trained single-stage regressor | 3.96 | **19.53% worse** |

A model that loses to doing nothing has not earned a place in the
interface. This version acts on that.

## What was removed from this build

Not disabled — removed, so the build cannot quietly grow the feature
back:

- `models/augment_future_score.py`
- `models/train_future_regression.py`
- `artifacts/future_score_augmentation.json`
- `artifacts/future_score_regressor.pkl`
- `artifacts/metrics_future_regression.json`
- `artifacts/model_info_future_regression.json`
- `artifacts/feature_columns_future_regression.json`

The tests that cover Output 2 skip themselves when their artifacts are
absent, which is why the suite still passes here.

## Accuracy in this build

Both shipped models, on held-out data:

| model | metric | validation | test |
|---|---|---|---|
| classifier (7-day class) | accuracy | **90.34%** | **97.69%** |
| classifier | ROC-AUC | 98.46% | 99.82% |
| classifier | macro F1 | 90.62% | 97.70% |
| regressor (today's score) | R² | **95.68%** | **99.17%** |
| regressor | MAE | 1.25 points | 0.50 points |

Validation is the number to quote: the test split flatters both models.

## Running it

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload      # http://127.0.0.1:8000
```

The mode is the built-in default. `DWAI_FUTURE_SCORE_MODE` still exists
as an override, but there is nothing in this build for `augmented` to
read, so it falls back rather than inventing a number.
