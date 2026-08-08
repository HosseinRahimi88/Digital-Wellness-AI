"""
api/main.py
--------------
FastAPI application factory. This file's only job is wiring: creating
the app, registering middleware/exception handlers/routers in the
right order, and configuring OpenAPI metadata. No business logic, no
service instantiation beyond what api.dependencies already provides.

Run with:
    uvicorn api.main:app --reload          # development
    uvicorn api.main:app --workers 4       # production (see Dockerfile)
"""

from __future__ import annotations

# Load .env into the real process environment BEFORE anything else runs.
# api.core.config.Settings (pydantic-settings) already reads .env for
# its own fields, but utils/tokens.py's get_jwt_secret() deliberately
# reads JWT_SECRET_KEY straight from os.environ (see that module's
# docstring - this API layer intentionally does not duplicate ownership
# of that secret into Settings). Without this load_dotenv() call, a
# JWT_SECRET_KEY set only in .env would be invisible to that function
# even though Settings itself would load fine - this was caught by
# actually booting the app and exercising /auth/register end-to-end,
# not assumed to work from reading the code.
from dotenv import load_dotenv

load_dotenv()

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from api.core.config import PROJECT_ROOT, get_settings
from api.core.logging_config import configure_logging
from api.dependencies.services import (
    get_account_service,
    get_cohort_service_cls,
    get_model_manager,
    get_persona_service,
    get_recommendation_service,
    get_report_service,
    get_validation_service,
)
from api.exceptions.handlers import register_exception_handlers
from api.middleware.request_context import (
    MaxBodySizeMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from api.routers import (
    analytics,
    auth,
    cohort,
    future_path,
    health,
    history,
    model_performance,
    parallel_twin,
    persona,
    plan,
    progress,
    prediction,
    reports,
    schema,
    whatif,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once at process startup, before the app accepts any
    requests, and once at shutdown.

    Startup: pre-warms every process-wide singleton this API depends
    on - most importantly ModelManager.instance(), which loads both
    trained model artifacts plus SHAP/uncertainty/persona set-up. Every
    one of these is already a singleton at the service layer (via
    functools.lru_cache in api/dependencies/services.py, or
    ModelManager's own .instance()) - this just forces that one-time
    construction to happen HERE, synchronously, before /health/ready
    can return 200, rather than lazily on whichever request happens to
    be first. Two concrete production problems this avoids:
      1. The first real user request after a deploy would otherwise
         silently pay the full model-load latency inline.
      2. An orchestrator (Kubernetes, ECS, ...) polling /health/ready
         during startup would see it succeed immediately (the route
         itself returns fast) while the FIRST call to that route is
         actually the one doing the slow work - misleading against
         exactly what a readiness probe is supposed to signal.
    Measured cold-load time (this environment, includes classifier +
    regressor + SHAP + uncertainty calibration + persona clustering):
    logged below at INFO on every startup, not hand-waved as "fast enough".
    """
    settings = get_settings()
    configure_logging(settings)

    logger.info("Starting up %s v%s", settings.app_name, settings.app_version)
    start = time.perf_counter()

    model_manager = get_model_manager()
    get_account_service()
    get_validation_service()
    get_recommendation_service()
    get_persona_service(model_manager)
    get_report_service()
    get_cohort_service_cls()

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("Startup complete in %.1fms - all singletons warm, ready to serve.", elapsed_ms)

    yield

    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "REST API for the Digital Wellness AI prediction, recommendation, "
            "and analytics engine. This is a thin HTTP interface over the "
            "existing services/ layer - every endpoint calls the same "
            "PredictionService, RecommendationService, HistoryService, etc. "
            "the Streamlit app uses, so results are identical between the "
            "two interfaces by construction, not by convention."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- Middleware (order matters: outermost added last runs first on
    # the way in / last on the way out) ---
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(MaxBodySizeMiddleware, max_bytes=settings.max_request_body_bytes)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    if settings.trusted_hosts_list and settings.trusted_hosts_list != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)
    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(schema.router, prefix=settings.api_prefix)
    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(prediction.router, prefix=settings.api_prefix)
    app.include_router(future_path.router, prefix=settings.api_prefix)
    app.include_router(parallel_twin.router, prefix=settings.api_prefix)
    app.include_router(whatif.router, prefix=settings.api_prefix)
    app.include_router(persona.router, prefix=settings.api_prefix)
    app.include_router(cohort.router, prefix=settings.api_prefix)
    app.include_router(history.router, prefix=settings.api_prefix)
    app.include_router(analytics.router, prefix=settings.api_prefix)
    app.include_router(reports.router, prefix=settings.api_prefix)
    app.include_router(plan.router, prefix=settings.api_prefix)
    app.include_router(model_performance.router, prefix=settings.api_prefix)
    app.include_router(progress.router, prefix=settings.api_prefix)

    # --- Static frontend (frontend/) ---
    # Mounted LAST and at "/" so it only ever catches requests that none
    # of the API routes above matched (Starlette checks routes in
    # registration order) - the vanilla HTML/CSS/JS frontend is served
    # from the same origin as the API, which sidesteps CORS entirely for
    # the normal case of opening this app straight from the backend.
    frontend_dir = PROJECT_ROOT / "frontend"
    if frontend_dir.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app


app = create_app()
