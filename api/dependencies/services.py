"""
api/dependencies/services.py
------------------------------
FastAPI dependency-injection providers for the existing services
layer. This module's entire job is construction/wiring - it never
contains business logic, only "how do I get an instance of X service
for this request".

Two categories:

1. Process-wide singletons (ModelManager, PredictionService,
   RecommendationService, ...) - these are already singletons/cached
   at the service layer itself (ModelManager.instance()), so the
   FastAPI dependency just returns the same shared instance every
   request, exactly like models/model_manager.py already intends for
   the Streamlit app. No new caching logic is introduced here.

2. Per-user services (HistoryService) - these take a user_id in their
   constructor, so the dependency reads the authenticated user's id
   (via api.auth.security.get_current_account) and constructs a
   request-scoped instance, exactly like every Streamlit page already
   does with HistoryService(user_id=...).
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from models.model_manager import ModelManager
from services.account_service import Account, AccountService
from services.cohort_service import CohortService
from services.history_service import HistoryService
from services.persona_service import PersonaService
from services.prediction_service import PredictionService
from services.recommendation_service import RecommendationService
from services.report_service import ReportService
from services.storage.base import StorageBackend
from services.validation_service import ValidationService


def get_model_manager() -> ModelManager:
    return ModelManager.instance()


@lru_cache(maxsize=1)
def _account_service_singleton() -> AccountService:
    # AccountService itself is stateless aside from its storage backend
    # (a JSON file), so one shared instance per process is correct -
    # matches how every Streamlit page constructs `AccountService()`
    # fresh but against the same underlying storage file.
    return AccountService()


def get_account_service() -> AccountService:
    return _account_service_singleton()


@lru_cache(maxsize=1)
def _validation_service_singleton() -> ValidationService:
    return ValidationService()


def get_validation_service() -> ValidationService:
    return _validation_service_singleton()


def get_prediction_service(
    model_manager: ModelManager = Depends(get_model_manager),
) -> PredictionService:
    # PredictionService is cheap to construct (it just holds a reference
    # to the already-loaded ModelManager singleton - see
    # services/prediction_service.py's own docstring on this) so a new
    # instance per request is fine and avoids any request-scoped mutable
    # state living longer than the request.
    return PredictionService(model_manager=model_manager)


@lru_cache(maxsize=1)
def _recommendation_service_singleton() -> RecommendationService:
    return RecommendationService()


def get_recommendation_service() -> RecommendationService:
    return _recommendation_service_singleton()


def get_persona_service(
    model_manager: ModelManager = Depends(get_model_manager),
) -> PersonaService:
    # ModelManager already constructs and owns exactly one PersonaService
    # (models/model_manager.py) - reuse that instance rather than
    # constructing a second, independent one here. An earlier version
    # of this function called `PersonaService()` directly, which loaded
    # the persona clustering artifact a second time into a second
    # object - confirmed via the lifespan startup log showing
    # "PersonaService loaded" twice on every process start.
    return model_manager.persona_service


@lru_cache(maxsize=1)
def _report_service_singleton() -> ReportService:
    return ReportService()


def get_report_service() -> ReportService:
    return _report_service_singleton()


def get_cohort_service_cls() -> type[CohortService]:
    # CohortService is all classmethods/staticmethods (its own cache is
    # a module-level functools.lru_cache in services/cohort_service.py),
    # so the "dependency" is just the class itself, not an instance.
    return CohortService


def get_history_service(
    account: Account,
    storage: StorageBackend | None = None,
) -> HistoryService:
    """Not itself a FastAPI dependency (it needs the authenticated
    account, which routers already depend on separately) - a small
    factory routers call directly: `get_history_service(account)`.
    Kept here rather than inlined in every router so the "one
    HistoryService per authenticated user" rule lives in one place.
    `storage` defaults to None, meaning HistoryService falls back to
    its own DEFAULT_STORAGE_PATH - identical behavior to every
    Streamlit page constructing HistoryService(user_id=...). Routers
    should not call this directly with a storage override; that's
    exactly what get_history_storage_backend() below exists to make
    overridable via FastAPI's dependency_overrides in tests, without
    ever touching the production data file."""
    return HistoryService(user_id=account.user_id, storage=storage) if storage else HistoryService(user_id=account.user_id)


def get_history_storage_backend() -> StorageBackend | None:
    """Returns None by default - HistoryService then uses its own real
    DEFAULT_STORAGE_PATH, exactly matching the Streamlit app. Exists
    purely so tests can do
    `app.dependency_overrides[get_history_storage_backend] = lambda: test_backend`
    to redirect every request-scoped HistoryService to an isolated
    temp-file backend instead, without ever writing to the real
    production history file during a test run.

    Deliberately not composed together with get_current_account into a
    single "get_history_service_dep" convenience dependency here: that
    would require importing api.auth.security.get_current_account into
    this module, which already imports FROM api.auth.security the
    other direction (get_account_service) - a circular import. Routers
    instead depend on get_current_account and this function separately,
    then call get_history_service(account, storage=storage) themselves;
    see api/routers/prediction.py for the pattern."""
    return None
