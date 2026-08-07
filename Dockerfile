# Digital Wellness AI - FastAPI backend production image.
#
# This image serves api/main.py ONLY (the FastAPI backend). The
# Streamlit app (app/Home.py) is a separate deployable and deliberately
# NOT started by this image - the two interfaces share the services/
# and artifacts/ layers but have different runtime characteristics
# (Streamlit's own dev server vs. a multi-worker ASGI server here) and
# should be deployed/scaled independently.
#
# Build:  docker build -t digital-wellness-api .
# Run:    docker run -p 8000:8000 --env-file .env digital-wellness-api

FROM python:3.12-slim AS base

# --- OS-level build dependencies -------------------------------------
# gcc/build-essential: some scientific-Python wheels (numba, in
# particular, which shap depends on) fall back to compiling from source
# on platforms without a prebuilt wheel - safer to have a compiler
# available than to have the image build fail on an unlucky platform.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python dependencies (separate layer for build-cache efficiency) --
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Application code ---------------------------------------------------
# Only what api/main.py's import graph actually needs at runtime -
# services/, models/, core/, config/, utils/, artifacts/, api/ itself.
# Explicitly NOT copied: app/ (the Streamlit UI - separate deployable),
# tests/, data/ (multi-hundred-MB training CSVs, never read outside
# training/evaluation scripts), storage/archive_*/ backups.
COPY api/ ./api/
COPY services/ ./services/
COPY models/ ./models/
COPY core/ ./core/
COPY config/ ./config/
COPY utils/ ./utils/
COPY artifacts/ ./artifacts/

# storage/ holds runtime data (accounts.json, prediction_history.json)
# that must persist across container restarts - mount a volume over it
# in production (see docker-compose.yml). Create it here with the
# correct starting shape so a fresh container works without a volume
# too (e.g. local testing).
RUN mkdir -p storage && \
    echo "[]" > storage/accounts.json && \
    echo "[]" > storage/prediction_history.json

# --- Runtime user (never run as root in a container) -------------------
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness: does the process respond at all. Kubernetes/ECS should use
# /health/ready (via an HTTP probe pointed at that path) for readiness,
# not this HEALTHCHECK instruction, which only covers liveness -
# distinct on purpose (see api/routers/health.py's docstrings).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

# --- Production startup -------------------------------------------------
# Multiple worker processes, each with its own copy of the loaded
# models (ModelManager is a per-process singleton, not shared across
# workers - see models/model_manager.py). WEB_CONCURRENCY lets the
# orchestrator size this per-container without rebuilding the image;
# defaults to 2, a reasonable starting point for a CPU-bound (model
# inference) workload sharing a single container's CPU allocation -
# tune based on actual container CPU limits and observed latency, not
# a number to trust blindly.
ENV WEB_CONCURRENCY=2
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY}"]
