"""
Tests: the FastAPI backend (api/) end-to-end via TestClient - real
HTTP requests through the real app, hitting the real services layer
(PredictionService, RecommendationService, HistoryService, ...), the
same way the Streamlit app does. No mocked business logic anywhere in
this file - only the storage BACKEND is swapped for an isolated
temp-file one (via FastAPI's dependency_overrides), so running this
suite never touches storage/accounts.json / storage/prediction_history.json,
the real files the deployed app itself would use.

Run: python3 -m unittest tests.api.test_api -v
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tests._test_support as ts  # noqa: F401 - installs offline pwdlib/shap stubs, sys.path bootstrap


def _memory_mail():
    """Route outbound mail into memory and return the transport.

    The reset and verification codes are no longer in any HTTP response,
    which is the entire point - so a test that needs one has to read it
    the way a user does, out of the message that was sent.
    """
    from services.identity.mail_service import (
        MailService, MemoryTransport, set_mail_service,
    )

    transport = MemoryTransport()
    set_mail_service(MailService(transport))
    return transport


def _code_from(body: str) -> str:
    """The token out of a mail body - the indented line the template puts it on."""
    match = re.search(r"^\s{4}(\S+)\s*$", body, re.M)
    assert match, f"no code found in mail body:\n{body}"
    return match.group(1)


TEST_JWT_SECRET = "x" * 40  # >=32 chars, matches tests/identity/test_tokens.py's own convention


class APITestCase(unittest.TestCase):
    """Base class: boots a real FastAPI app per test with isolated
    account + history storage, so no test run ever touches the real
    storage/*.json files or leaks state between tests."""

    def setUp(self):
        self._env_patch = patch.dict(os.environ, {"JWT_SECRET_KEY": TEST_JWT_SECRET})
        self._env_patch.start()

        # Import inside setUp (not module scope): api.main reads
        # JWT_SECRET_KEY-adjacent config at import time in some paths,
        # so the env patch must already be active first.
        from fastapi.testclient import TestClient

        from api.main import app
        from api.dependencies.services import (
            get_account_service,
            get_history_storage_backend,
            get_plan_side_storage_backend,
        )
        from services.identity.account_service import AccountService
        from services.storage.json_file_storage import JSONFileStorageBackend

        self._tmp_dir = Path(tempfile.mkdtemp())
        accounts_backend = JSONFileStorageBackend(self._tmp_dir / "accounts.json")
        history_backend = JSONFileStorageBackend(self._tmp_dir / "history.json")
        # The weekly plan's own three stores (frozen snapshot, day
        # decisions, violation ledger). Separate from history on
        # purpose - HistoryService selects by user_id alone, so a shared
        # backend would surface a plan snapshot as a check-in. Without
        # this override a test run writes to the real storage/*.json.
        plan_side_backend = JSONFileStorageBackend(self._tmp_dir / "plan_side.json")
        # Exposed so a test can construct PlanLockService /
        # DayDecisionService / ViolationService against the same store
        # the app is using, instead of against the production default.
        self._plan_side_backend = plan_side_backend

        self._test_account_service = AccountService(backend=accounts_backend)

        app.dependency_overrides[get_account_service] = lambda: self._test_account_service
        app.dependency_overrides[get_history_storage_backend] = lambda: history_backend
        app.dependency_overrides[get_plan_side_storage_backend] = lambda: plan_side_backend

        self.app = app
        self.client = TestClient(app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self._env_patch.stop()

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _register(self, email: str = "user@example.com", password: str = "testpass123", display_name: str = "Test User") -> str:
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "display_name": display_name},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["access_token"]

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


class TestHealth(APITestCase):

    def test_health_returns_200(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_readiness_confirms_models_loaded(self):
        response = self.client.get("/health/ready")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["models_loaded"])
        self.assertTrue(response.json()["classification_model"])
        self.assertTrue(response.json()["regression_model"])


class TestAuth(APITestCase):

    def test_register_returns_access_token(self):
        token = self._register()
        self.assertTrue(token)

    def test_duplicate_email_returns_409(self):
        self._register(email="dup@example.com")
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": "dup@example.com", "password": "testpass123", "display_name": "Second"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "email_already_registered")

    def test_login_with_wrong_password_returns_401(self):
        self._register(email="wrongpass@example.com", password="correct123")
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "wrongpass@example.com", "password": "incorrect123"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "invalid_credentials")

    def test_login_with_correct_password_succeeds(self):
        self._register(email="login@example.com", password="correct123")
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "correct123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["access_token"])

    def test_me_requires_authentication(self):
        response = self.client.get("/api/v1/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "unauthorized")

    def test_me_with_valid_token_returns_account(self):
        token = self._register(email="me@example.com", display_name="Me Test")
        response = self.client.get("/api/v1/auth/me", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "me@example.com")
        self.assertEqual(response.json()["display_name"], "Me Test")

    def test_me_with_garbage_token_returns_401(self):
        response = self.client.get("/api/v1/auth/me", headers=self._auth_headers("not-a-real-token"))
        self.assertEqual(response.status_code, 401)

    def test_onboarding_profile_round_trips(self):
        token = self._register(email="onboard@example.com")
        response = self.client.put(
            "/api/v1/auth/me/onboarding",
            headers=self._auth_headers(token),
            json={
                "primary_goal": "reduce_screen_time", "main_use_purpose": "work",
                "schedule_type": "standard", "usual_sleep_time": "23:00",
                "usual_wake_time": "07:00", "preferred_effort": "medium",
                "work_screen_required": True,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["onboarding_complete"])
        self.assertEqual(response.json()["primary_goal"], "reduce_screen_time")

    def test_forgot_password_never_puts_the_reset_code_in_the_response(self):
        # THE regression. This response used to carry `reset_token`,
        # which made knowing somebody's email address sufficient to take
        # their account: POST the address, read the token out of the
        # JSON, set a new password. Nothing in the body may carry it -
        # not under the old key, not under a new one - so the whole
        # payload is searched for the code that was actually issued.
        self._register(email="forgot@example.com", password="original123")
        mail = _memory_mail()
        response = self.client.post(
            "/api/v1/auth/forgot-password", json={"email": "forgot@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("reset_token", body)

        message = mail.last_to("forgot@example.com")
        self.assertIsNotNone(message, "no reset mail was sent")
        code = _code_from(message.body)
        self.assertNotIn(code, json.dumps(body), "the reset code is in the response body")

    def test_forgot_password_answers_identically_for_an_unknown_address(self):
        # Neither field may distinguish a registered address from an
        # unregistered one, or this route becomes an account enumerator.
        self._register(email="known@example.com", password="original123")
        _memory_mail()
        known = self.client.post("/api/v1/auth/forgot-password", json={"email": "known@example.com"})
        unknown = self.client.post(
            "/api/v1/auth/forgot-password", json={"email": "nobody-at-all@example.com"},
        )
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.json()["message"], unknown.json()["message"])

    def test_forgot_password_says_where_the_code_went(self):
        # A user who is told "check your email" when there is no mail
        # server waits for something that will never arrive.
        self._register(email="channel@example.com", password="original123")
        _memory_mail()
        sent = self.client.post("/api/v1/auth/forgot-password", json={"email": "channel@example.com"})
        self.assertEqual(sent.json()["delivery"], "email")

    def test_reset_password_with_valid_token_logs_in_with_new_password(self):
        self._register(email="reset@example.com", password="original123")
        mail = _memory_mail()
        self.client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
        token = _code_from(mail.last_to("reset@example.com").body)

        response = self.client.post(
            "/api/v1/auth/reset-password", json={"reset_token": token, "new_password": "brandnew123"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["access_token"])

        # Old password no longer works, new one does.
        old = self.client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "original123"})
        self.assertEqual(old.status_code, 401)
        new = self.client.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "brandnew123"})
        self.assertEqual(new.status_code, 200)

    def test_reset_password_rejects_garbage_token(self):
        response = self.client.post(
            "/api/v1/auth/reset-password", json={"reset_token": "not-a-real-token", "new_password": "brandnew123"},
        )
        self.assertEqual(response.status_code, 401)

    def test_reset_password_cannot_be_done_with_a_regular_access_token(self):
        """A leaked/expired access token must never double as a password
        reset credential - only a token minted by forgot-password works."""
        access_token = self._register(email="notareset@example.com")
        response = self.client.post(
            "/api/v1/auth/reset-password", json={"reset_token": access_token, "new_password": "brandnew123"},
        )
        self.assertEqual(response.status_code, 401)


class TestPrediction(APITestCase):

    def test_predict_requires_authentication(self):
        import config.demo_profiles as dp
        response = self.client.post("/api/v1/predict", json={"user_data": dp.healthy_profile()})
        self.assertEqual(response.status_code, 401)

    def test_healthy_profile_predicts_healthy_with_no_recommendations(self):
        """Same real-pipeline behavior verified directly against the
        services in the prior audit session: a genuinely healthy
        profile's SHAP-driven recommendations should come back empty,
        not a 'fix your best trait' recommendation - now verified
        through the actual HTTP layer, not just the service call."""
        import config.demo_profiles as dp
        token = self._register(email="healthy@example.com")
        response = self.client.post(
            "/api/v1/predict",
            json={"user_data": dp.healthy_profile()},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["prediction"], "Healthy")
        self.assertEqual(body["recommendations"], [])
        self.assertTrue(body["persisted"])
        self.assertIsNotNone(body["uncertainty"])
        self.assertTrue(body["uncertainty"]["available"])

    def test_at_risk_profile_gets_targeted_recommendations(self):
        import config.demo_profiles as dp
        token = self._register(email="atrisk@example.com")
        response = self.client.post(
            "/api/v1/predict",
            json={"user_data": dp.at_risk_profile()},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["prediction"], "At Risk")
        self.assertGreater(len(body["recommendations"]), 0)
        for rec in body["recommendations"]:
            self.assertIn("title", rec)
            self.assertIn("priority", rec)

    def test_recommendations_carry_priority_and_safety_note_in_four_languages(self):
        # coach.js and app.js both used to render `priority` and
        # `safety_note` as raw English regardless of the reader's
        # language - text_i18n covered title/description/action/
        # success_metric but not these two, since they're shared across
        # rules rather than per-rule text. Checked through the real HTTP
        # response, the shape a browser actually receives.
        import config.demo_profiles as dp
        token = self._register(email="priority-i18n@example.com")
        response = self.client.post(
            "/api/v1/predict",
            json={"user_data": dp.at_risk_profile()},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        recs = response.json()["recommendations"]
        self.assertGreater(len(recs), 0)
        for rec in recs:
            self.assertIn("priority_i18n", rec)
            self.assertIn("safety_note_i18n", rec)
            for lang in ("en", "fa", "ar", "zh"):
                self.assertTrue(rec["priority_i18n"].get(lang, "").strip(),
                                 f"{rec['source_field']}.priority_i18n.{lang} empty")
                self.assertTrue(rec["safety_note_i18n"].get(lang, "").strip(),
                                 f"{rec['source_field']}.safety_note_i18n.{lang} empty")
            # The English value must still be a real translation, not the
            # raw enum echoed back - "high"/"medium"/"low" would pass a
            # naive non-empty check while still being untranslated.
            self.assertIn(rec["priority_i18n"]["en"].lower(), {"high", "medium", "low"})
            self.assertEqual(rec["priority_i18n"]["en"].lower(), rec["priority"].lower())

    def test_invalid_feature_value_returns_422_with_field_errors(self):
        import config.demo_profiles as dp
        token = self._register(email="invalid@example.com")
        bad_profile = dict(dp.healthy_profile())
        bad_profile["age"] = 500  # far outside schema range
        response = self.client.post(
            "/api/v1/predict",
            json={"user_data": bad_profile},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "validation_failed")
        self.assertIn("age", response.json()["error"]["field_errors"])

    def test_persist_false_does_not_appear_in_history(self):
        import config.demo_profiles as dp
        token = self._register(email="nopersist@example.com")
        headers = self._auth_headers(token)

        response = self.client.post(
            "/api/v1/predict",
            json={"user_data": dp.healthy_profile(), "persist": False},
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["persisted"])

        history_response = self.client.get("/api/v1/history", headers=headers)
        self.assertEqual(history_response.json()["pagination"]["total_items"], 0)

    def test_predict_then_appears_in_history(self):
        import config.demo_profiles as dp
        token = self._register(email="withhistory@example.com")
        headers = self._auth_headers(token)

        self.client.post("/api/v1/predict", json={"user_data": dp.healthy_profile()}, headers=headers)
        history_response = self.client.get("/api/v1/history", headers=headers)
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.json()["pagination"]["total_items"], 1)
        self.assertEqual(history_response.json()["items"][0]["health_class"], "Healthy")


class TestFuturePathAndTwinAndWhatIf(APITestCase):

    def test_future_path_definitions_lists_five_paths(self):
        response = self.client.get("/api/v1/future-path/definitions")
        self.assertEqual(response.status_code, 200)
        keys = {p["key"] for p in response.json()}
        self.assertEqual(keys, {"status_quo", "continued_drift", "gradual_improvement", "committed_change", "digital_detox"})

    def test_future_path_compare_ranks_status_quo_against_alternatives(self):
        import config.demo_profiles as dp
        token = self._register(email="futurepath@example.com")
        response = self.client.post(
            "/api/v1/future-path/compare",
            json={"user_data": dp.healthy_profile()},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(len(body["paths"]), 5)
        self.assertIsNotNone(body["best_path_key"])

    def test_parallel_twin_available_for_at_risk_profile(self):
        import config.demo_profiles as dp
        token = self._register(email="twin@example.com")
        response = self.client.post(
            "/api/v1/parallel-twin/compare",
            json={"user_data": dp.at_risk_profile()},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["available"])
        self.assertGreater(len(response.json()["adjustments"]), 0)

    def test_whatif_sweep_returns_requested_number_of_points(self):
        import config.demo_profiles as dp
        token = self._register(email="sweep@example.com")
        response = self.client.post(
            "/api/v1/whatif/sweep",
            json={"user_data": dp.healthy_profile(), "field": "stress_0_10", "num_points": 6},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["points"]), 6)


class TestPersonaAndCohort(APITestCase):

    def test_persona_assignment_available_for_valid_profile(self):
        import config.demo_profiles as dp
        token = self._register(email="persona@example.com")
        response = self.client.post(
            "/api/v1/personas/assign",
            json={"user_data": dp.healthy_profile()},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["available"])
        self.assertTrue(response.json()["persona_name"])

    def test_cohort_availability(self):
        """The endpoint has to answer either way. data/ is gitignored, so
        a packaged build reports available=False - and reporting that
        honestly is the behaviour, not a fault. What must never happen is
        a build claiming a cohort it cannot read."""
        response = self.client.get("/api/v1/cohorts/availability")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("available", payload)
        if payload["available"]:
            self.assertGreater(payload["cohort_size"], 0)
        else:
            self.assertEqual(payload["cohort_size"], 0)

    def test_cohort_summary_unknown_field_returns_404(self):
        response = self.client.get("/api/v1/cohorts/summary", params={"field": "not_a_real_field"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "cohort_field_unavailable")


class TestHistoryAndAnalyticsIsolation(APITestCase):
    """Confirms two different authenticated users never see each
    other's history/analytics - the core multi-tenancy guarantee this
    API layer must preserve from the existing per-user HistoryService."""

    def test_two_users_have_independent_history(self):
        import config.demo_profiles as dp

        token_a = self._register(email="usera@example.com")
        token_b = self._register(email="userb@example.com")

        self.client.post("/api/v1/predict", json={"user_data": dp.healthy_profile()}, headers=self._auth_headers(token_a))

        history_a = self.client.get("/api/v1/history", headers=self._auth_headers(token_a))
        history_b = self.client.get("/api/v1/history", headers=self._auth_headers(token_b))

        self.assertEqual(history_a.json()["pagination"]["total_items"], 1)
        self.assertEqual(history_b.json()["pagination"]["total_items"], 0)

    def test_analytics_reflects_only_the_authenticated_users_entries(self):
        import config.demo_profiles as dp

        token = self._register(email="analytics@example.com")
        headers = self._auth_headers(token)
        self.client.post("/api/v1/predict", json={"user_data": dp.healthy_profile()}, headers=headers)

        response = self.client.get("/api/v1/analytics/summary", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["entry_count"], 1)


class TestSchemaAndOpenAPI(APITestCase):

    def test_feature_schema_endpoint_matches_real_feature_schema(self):
        from core.feature_schema import FEATURE_SCHEMA

        response = self.client.get("/api/v1/schema/features")
        self.assertEqual(response.status_code, 200)
        names = {f["name"] for f in response.json()}
        self.assertEqual(names, set(FEATURE_SCHEMA.keys()))

    def test_openapi_schema_is_valid_json_and_lists_documented_paths(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("/api/v1/predict", body["paths"])
        self.assertIn("/health", body["paths"])

    def test_docs_ui_is_served(self):
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)


class TestReports(APITestCase):

    def test_pdf_report_generation_returns_pdf_bytes(self):
        import config.demo_profiles as dp
        token = self._register(email="report@example.com")
        response = self.client.post(
            "/api/v1/reports/pdf",
            json={"user_data": dp.healthy_profile()},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))


class TestLifespan(unittest.TestCase):
    """Unlike APITestCase's plain TestClient(app) (which never triggers
    startup/shutdown events - only the context-manager form does), this
    verifies the lifespan hook in api/main.py actually runs: singletons
    get pre-warmed before the app is considered ready, not lazily on
    first request."""

    def setUp(self):
        self._env_patch = patch.dict(os.environ, {"JWT_SECRET_KEY": TEST_JWT_SECRET})
        self._env_patch.start()

    def tearDown(self):
        self._env_patch.stop()

    def test_lifespan_prewarms_model_manager_before_first_request(self):
        """Two things this actually proves: (1) the lifespan startup
        hook runs without raising - entering the context manager would
        fail otherwise, since FastAPI surfaces a startup exception at
        __enter__; (2) /health/ready succeeds as the very first request
        against a freshly-entered client, meaning the readiness check
        itself never has to pay a lazy-load cost. It can't additionally
        prove ordering relative to lazy-loading in isolation - once any
        test in the same process has touched ModelManager.instance(),
        that singleton stays warm process-wide, so a same-process
        before/after timing comparison isn't meaningful here."""
        from fastapi.testclient import TestClient
        from api.main import app
        from models.model_manager import ModelManager

        with TestClient(app) as client:
            response = client.get("/health/ready")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["models_loaded"])
            self.assertIsNotNone(ModelManager.instance())


class TestMiddleware(APITestCase):

    def test_oversized_request_body_returns_413(self):
        big_body = b"x" * 3_000_000  # over the 2MB default limit
        response = self.client.post(
            "/api/v1/auth/register",
            content=big_body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(big_body))},
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "payload_too_large")

    def test_normal_sized_request_is_not_rejected(self):
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": "normalsize@example.com", "password": "testpass123", "display_name": "Normal"},
        )
        self.assertEqual(response.status_code, 201)

    def test_response_includes_request_id_and_timing_headers(self):
        response = self.client.get("/health")
        self.assertIn("x-request-id", response.headers)
        self.assertIn("x-response-time-ms", response.headers)

    def test_response_includes_security_headers(self):
        response = self.client.get("/health")
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(response.headers.get("x-frame-options"), "DENY")


class TestDependencyDeduplication(unittest.TestCase):
    """Regression test for a real bug found during the production
    audit: api.dependencies.services.get_persona_service() used to
    construct its own independent PersonaService() instead of reusing
    the one ModelManager already owns and loads at startup - silently
    doubling persona-artifact load time and memory on every process
    start. Confirmed via this exact assertion before the fix (it failed:
    two different objects) and after (passes: the same object)."""

    def setUp(self):
        self._env_patch = patch.dict(os.environ, {"JWT_SECRET_KEY": TEST_JWT_SECRET})
        self._env_patch.start()

    def tearDown(self):
        self._env_patch.stop()

    def test_get_persona_service_reuses_model_managers_instance(self):
        import tests._test_support  # noqa: F401
        from api.dependencies.services import get_model_manager, get_persona_service

        model_manager = get_model_manager()
        persona_service = get_persona_service(model_manager)
        self.assertIs(persona_service, model_manager.persona_service)


if __name__ == "__main__":
    unittest.main()
