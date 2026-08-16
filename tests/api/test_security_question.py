"""
Tests: the second way back into an account.

WHY THIS EXISTS. `/auth/forgot-password` mints a reset code and hands it
to services/identity/mail_service. With no mail server configured -
which is what this project actually ships with - that transport is
`LogTransport`, so the code goes to the server's log. The person who
needs it cannot read the server's log. For a real user of a real
deployment of this app, the emailed route is a dead end, and "reset your
password" is a button that does nothing they can act on.

The security question is the way back that does not depend on somebody
else's mail infrastructure. It is set at REGISTRATION, because the
moment somebody needs it is the moment they cannot sign in to set it.

WHAT IS WORTH PINNING. A recovery route is a way INTO an account, so
every test below is really asking the same question - can this be used
by somebody who is not the owner:

  - the answer is stored hashed and never leaves the server;
  - a wrong answer, an unknown address and an account with no question
    are one indistinguishable failure, so this cannot be used to find
    out which addresses are registered;
  - guessing is throttled, sharing login's counter - an answer carries
    less entropy than a password, which makes this the softest target
    in the app;
  - recovering an account withdraws every session that account had,
    because somebody recovering an account is usually recovering it
    FROM someone;
  - and changing the question requires the current password, so a
    borrowed session cannot rewrite the way back in.

Run: python3 -m unittest tests.api.test_security_question -v
"""

from __future__ import annotations

import tests._test_support as ts  # noqa: F401 - offline stubs + sys.path

from tests.api.test_api import APITestCase

QUESTION = "What did I name my first bike?"
ANSWER = "Blue Rocket"


class TestSecurityQuestion(APITestCase):

    def setUp(self):
        super().setUp()
        self.email = "recover@example.com"
        self.password = "OriginalPass123!"

    # ---------------------------------------------------------- helpers
    def _register(self, *, with_question=True, email=None, password=None):
        body = {
            "email": email or self.email,
            "password": password or self.password,
            "display_name": "Recoverable",
        }
        if with_question:
            body["security_question"] = QUESTION
            body["security_answer"] = ANSWER
        return self.client.post("/api/v1/auth/register", json=body)

    def _ask(self, email=None):
        return self.client.post(
            "/api/v1/auth/security-question", json={"email": email or self.email},
        )

    def _answer(self, answer, new_password="BrandNewPass456!", email=None):
        return self.client.post(
            "/api/v1/auth/reset-password-with-answer",
            json={
                "email": email or self.email,
                "answer": answer,
                "new_password": new_password,
            },
        )

    def _login(self, password, email=None):
        return self.client.post(
            "/api/v1/auth/login",
            json={"email": email or self.email, "password": password},
        )

    # ------------------------------------------------------ registration
    def test_a_question_set_at_registration_can_be_read_back(self):
        self.assertEqual(self._register().status_code, 201)
        body = self._ask().json()
        self.assertEqual(body["question"], QUESTION)
        self.assertTrue(body["available"])

    def test_registering_without_one_is_still_allowed(self):
        """A client written before this existed must keep working, and a
        user who does not want to set one is not blocked from signing up."""
        response = self._register(with_question=False)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertIsNone(self._ask().json()["question"])

    def test_half_a_question_is_refused(self):
        for half in ({"security_question": QUESTION}, {"security_answer": ANSWER}):
            body = {
                "email": f"half{len(half)}@example.com",
                "password": self.password,
                "display_name": "Half",
                **half,
            }
            response = self.client.post("/api/v1/auth/register", json=body)
            self.assertEqual(response.status_code, 400, response.text)

    def test_a_one_character_answer_is_refused(self):
        response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com", "password": self.password,
                "display_name": "Short",
                "security_question": QUESTION, "security_answer": "x",
            },
        )
        self.assertEqual(response.status_code, 400, response.text)

    # ------------------------------------------------------- the answer
    def test_the_right_answer_sets_a_new_password_and_signs_in(self):
        self._register()
        response = self._answer(ANSWER)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["access_token"])
        # And the new password is the one that works now.
        self.assertEqual(self._login("BrandNewPass456!").status_code, 200)
        self.assertEqual(self._login(self.password).status_code, 401)

    def test_the_answer_is_not_case_or_space_sensitive(self):
        """Nobody reproduces their own capitalisation months later, and
        locking somebody out of their account over a shift key is the
        failure mode that makes people abandon recovery flows."""
        self._register()
        self.assertEqual(self._answer("  blue   rocket ").status_code, 200)

    def test_a_wrong_answer_changes_nothing(self):
        self._register()
        self.assertEqual(self._answer("Red Rocket").status_code, 401)
        # The original password still works, which is the thing that
        # matters: a failed recovery must not be a partial one.
        self.assertEqual(self._login(self.password).status_code, 200)

    def test_a_short_new_password_is_refused_even_with_the_right_answer(self):
        self._register()
        response = self._answer(ANSWER, new_password="x")
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self._login(self.password).status_code, 200)

    # -------------------------------------------------- not a directory
    def test_an_unregistered_address_looks_exactly_like_a_missing_question(self):
        """Otherwise this endpoint answers "does this person have an
        account here", which is a question nobody outside is entitled
        to ask of a wellbeing app."""
        self._register(with_question=False)
        stranger = self._ask("nobody@example.com").json()
        no_question = self._ask().json()
        self.assertEqual(stranger, no_question)

    def test_answering_for_an_unknown_address_fails_like_a_wrong_answer(self):
        self._register()
        unknown = self._answer(ANSWER, email="nobody@example.com")
        wrong = self._answer("Red Rocket")
        self.assertEqual(unknown.status_code, wrong.status_code)
        self.assertEqual(
            unknown.json()["error"]["code"], wrong.json()["error"]["code"],
        )

    # ------------------------------------------------------ the secrets
    def test_the_answer_never_appears_in_any_response(self):
        self._register()
        headers = self._auth_headers(self._login(self.password).json()["access_token"])
        bodies = [
            self._ask().text,
            self.client.get("/api/v1/auth/me", headers=headers).text,
            self._answer("wrong").text,
        ]
        for body in bodies:
            self.assertNotIn(ANSWER, body)
            self.assertNotIn(ANSWER.lower(), body.lower())

    def test_the_answer_is_stored_hashed(self):
        self._register()
        stored = self._test_account_service.get_by_email(self.email)
        self.assertTrue(stored.security_answer_hash)
        self.assertNotIn(ANSWER.lower(), stored.security_answer_hash.lower())
        self.assertTrue(stored.security_answer_hash.startswith("$argon2"))

    # -------------------------------------------------------- throttled
    def test_guessing_is_throttled(self):
        """An answer is lower-entropy than a password, so this is the
        softest target in the app. It shares login's counter, which also
        means guessing here burns the login budget."""
        self._register()
        codes = [self._answer(f"guess-{i}").status_code for i in range(8)]
        self.assertIn(429, codes, f"never throttled: {codes}")

    # -------------------------------------------- recovering FROM someone
    def test_recovering_ends_every_session_the_account_had(self):
        self._register()
        session = self._login(self.password).json()
        refresh = session["refresh_token"]
        self.assertEqual(self._answer(ANSWER).status_code, 200)
        spent = self.client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        self.assertEqual(
            spent.status_code, 401,
            "the session that existed before the recovery still works - the "
            "recovery is cosmetic against exactly the person it is for",
        )

    # ------------------------------------------------ setting it later
    def test_an_existing_account_can_add_one(self):
        self._register(with_question=False)
        headers = self._auth_headers(self._login(self.password).json()["access_token"])
        response = self.client.post(
            "/api/v1/auth/security-question/set", headers=headers,
            json={
                "question": QUESTION, "answer": ANSWER,
                "current_password": self.password,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["has_security_question"])
        self.assertEqual(self._ask().json()["question"], QUESTION)

    def test_changing_it_needs_the_current_password(self):
        """A borrowed session must not be able to rewrite the way back
        in - that turns a recovery feature into a takeover feature."""
        self._register()
        headers = self._auth_headers(self._login(self.password).json()["access_token"])
        response = self.client.post(
            "/api/v1/auth/security-question/set", headers=headers,
            json={
                "question": "What is my cat called?", "answer": "Mishka",
                "current_password": "not-the-password",
            },
        )
        self.assertEqual(response.status_code, 401, response.text)
        # And the original question is untouched.
        self.assertEqual(self._ask().json()["question"], QUESTION)

    def test_the_account_endpoint_reports_whether_one_is_set(self):
        self._register(with_question=False)
        headers = self._auth_headers(self._login(self.password).json()["access_token"])
        me = self.client.get("/api/v1/auth/me", headers=headers).json()
        self.assertFalse(me["has_security_question"])
        self.assertIsNone(me["security_question"])
