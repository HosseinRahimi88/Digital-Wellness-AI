# Documentation

Start with the [project README](../README.md). These are here for
investigating a specific claim — each one exists because somebody would
otherwise have to take a number on trust.

## Which build is this

| Document | What it decided |
|---|---|
| [`VERSION_2_AUGMENTED.md`](VERSION_2_AUGMENTED.md) | **The shipped build.** How the seven-day figure is produced, and what was rejected. |
| [`VERSION_1_CLASS_ONLY.md`](VERSION_1_CLASS_ONLY.md) | The earlier build, which refused to show a seven-day number at all. Frozen. |

## How the models were arrived at

| Document | What it covers |
|---|---|
| [`reports/ML_AUDIT_REPORT.md`](reports/ML_AUDIT_REPORT.md) | The pipeline, end to end |
| [`reports/LEAKAGE_FIX_REPORT.md`](reports/LEAKAGE_FIX_REPORT.md) · [`reports/USER_LEAKAGE_FIX_REPORT.md`](reports/USER_LEAKAGE_FIX_REPORT.md) | Why the split is grouped, and what the ungrouped one was hiding |
| [`reports/BAND_MODEL_REPORT.md`](reports/BAND_MODEL_REPORT.md) | The weekly band: why a constant was wrong, and what the band actually reads |

## How the app was arrived at

| Document | What it covers |
|---|---|
| [`reports/PROJECT_MAP.md`](reports/PROJECT_MAP.md) | Where everything is and why |
| [`reports/FASTAPI_MIGRATION_REPORT.md`](reports/FASTAPI_MIGRATION_REPORT.md) | Streamlit → FastAPI |
| [`reports/HARDENING_REPORT.md`](reports/HARDENING_REPORT.md) | The account-takeover fix, sessions, drift, SQLite |
| [`reports/FINAL_QA_REPORT.md`](reports/FINAL_QA_REPORT.md) | Every sweep run against this build, and what it found |
| [`reports/PRODUCTION_READINESS_AUDIT.md`](reports/PRODUCTION_READINESS_AUDIT.md) | What would need to change to deploy it |
| [`../SECURITY.md`](../SECURITY.md) | Including one issue documented rather than hidden |

## Dated records

`AUDIT_REPORT`, `MERGE_REPORT` and `PROJECT_STATUS` describe the
repository as it was on the day each was written, not as it is now.
They are kept because they say *why* something is the way it is, which
no amount of reading the code recovers. Everything above is current.
