# Legacy

Code that is kept on purpose and is not part of the running app.

## `streamlit_app/`

The original Streamlit UI, from before the FastAPI backend and the
vanilla-JS frontend existed. It was the whole product once, and the
migration is documented in
[`docs/reports/FASTAPI_MIGRATION_REPORT.md`](../docs/reports/FASTAPI_MIGRATION_REPORT.md).

It is kept because it is provenance: it shows what the services layer was
extracted *from*, and it still imports the same `services/` and reads the
same `artifacts/` the real app does, so it demonstrates that the
extraction was real rather than a rename.

It is **not** started by `run.py` or by the Dockerfile, nothing in `api/`
or `services/` imports it, and it is not maintained alongside the primary
frontend. It lives here rather than at the repository root so that its
status is visible from the directory listing rather than only from a
paragraph in the README - somebody opening this project for the first
time should not have to be told which of two UIs is the real one.

Running it needs `streamlit` (not in `requirements.txt`):

```bash
pip install streamlit
streamlit run legacy/streamlit_app/Home.py
```
