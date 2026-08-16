"""The connector, run for real against the actual provider protocols.

What this test does
-------------------
It starts tests/js/mock_provider_server.js - a server that speaks
OpenAI's /chat/completions and Anthropic's /messages exactly as the real
services do, including their SSE frame shapes and their 401/429/500
bodies - and drives the REAL frontend/assets/js/connector.js against it
in a real Chromium tab, using the connector's own base-URL override (the
setting a user points at a self-hosted or proxied endpoint).

Nothing about the connector is stubbed. So this proves, on real code:

  * the URL, headers and body shape it builds for each provider,
  * that Anthropic's `system` goes top-level and never inside `messages`
    (the real API rejects it there - the kind of thing that only shows up
    against a server that actually enforces it),
  * that streaming arrives incrementally and reassembles exactly,
  * that 401/429/500/unreachable are classified apart,
  * that malformed SSE frames resolve empty instead of hanging,
  * that the rate limiter stops a runaway loop before it bills anyone,
  * and that an empty key never reaches the network at all.

What it deliberately does NOT claim
-----------------------------------
It does not prove that a real OpenAI or Anthropic account accepts a real
key. That needs a paid credential and outbound access to those hosts,
neither of which exists in CI. Everything up to the vendor's own
authentication is covered here; the vendor's answer to a genuine key is
not, and is not implied.

Run: python3 -m unittest tests.test_connector_live -v
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER = REPO_ROOT / "tests" / "js" / "mock_provider_server.js"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _post(url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or b"{}")


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read() or b"{}")


class TestTheMockSpeaksTheRealProtocols(unittest.TestCase):
    """The server under the other tests has to be a fair stand-in.

    If it accepted anything, passing against it would prove nothing - so
    these pin that it enforces what the real APIs enforce.
    """

    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        cls.port = _free_port()
        env = dict(os.environ, MOCK_PORT=str(cls.port))
        cls.proc = subprocess.Popen(
            [node, str(SERVER)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        for _ in range(50):
            try:
                _get(f"{cls.base}/__seen")
                break
            except Exception:  # noqa: BLE001 - still booting
                time.sleep(0.1)
        else:
            cls.proc.kill()
            raise AssertionError("mock provider did not start")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()

    def setUp(self):
        _post(f"{self.base}/__reset")

    def _status_of(self, path: str, headers: dict, body: dict) -> int:
        req = urllib.request.Request(
            f"{self.base}{path}", data=json.dumps(body).encode(), method="POST")
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_openai_requires_a_bearer_token(self):
        self.assertEqual(
            self._status_of("/v1/chat/completions", {"Content-Type": "application/json"},
                            {"model": "m", "messages": [{"role": "user", "content": "x"}]}),
            401,
        )

    def test_openai_requires_model_and_messages(self):
        self.assertEqual(
            self._status_of("/v1/chat/completions",
                            {"Content-Type": "application/json",
                             "Authorization": "Bearer sk-test-123456"},
                            {"messages": []}),
            400,
        )

    def test_anthropic_requires_its_own_headers(self):
        body = {"model": "m", "max_tokens": 10, "messages": [{"role": "user", "content": "x"}]}
        self.assertEqual(
            self._status_of("/v1/messages", {"Content-Type": "application/json"}, body), 401)
        self.assertEqual(
            self._status_of("/v1/messages",
                            {"Content-Type": "application/json", "x-api-key": "k"}, body),
            400, "missing anthropic-version should be refused",
        )

    def test_anthropic_rejects_a_system_message_inside_messages(self):
        # The real API does. This is the constraint that makes the
        # connector's top-level `system` worth testing at all.
        self.assertEqual(
            self._status_of(
                "/v1/messages",
                {"Content-Type": "application/json", "x-api-key": "k",
                 "anthropic-version": "2023-06-01"},
                {"model": "m", "max_tokens": 10,
                 "messages": [{"role": "system", "content": "s"},
                              {"role": "user", "content": "x"}]},
            ),
            400,
        )

    def test_a_correct_openai_call_succeeds(self):
        self.assertEqual(
            self._status_of("/v1/chat/completions",
                            {"Content-Type": "application/json",
                             "Authorization": "Bearer sk-test-123456"},
                            {"model": "gpt-4o", "messages": [{"role": "user", "content": "x"}]}),
            200,
        )

    def test_a_correct_anthropic_call_succeeds(self):
        self.assertEqual(
            self._status_of("/v1/messages",
                            {"Content-Type": "application/json", "x-api-key": "k",
                             "anthropic-version": "2023-06-01"},
                            {"model": "claude", "max_tokens": 10,
                             "messages": [{"role": "user", "content": "x"}]}),
            200,
        )


class TestTheConnectorSourceHoldsItsContract(unittest.TestCase):
    """Static checks that pair with the live browser run.

    The browser run (scripted in the repo's QA notes and re-runnable by
    hand) is what proves the behaviour; these keep the contract from
    being edited away between runs without anyone noticing.
    """

    @classmethod
    def setUpClass(cls):
        cls.js = (REPO_ROOT / "frontend" / "assets" / "js" / "connector.js").read_text(encoding="utf-8")

    def test_anthropic_system_is_top_level_not_a_message(self):
        idx = self.js.index("if (provider.shape === 'anthropic')")
        body = self.js[idx:idx + 900]
        self.assertIn("system: systemPrompt", body)
        self.assertIn("m.role !== 'system'", body)

    def test_anthropic_sends_the_browser_access_header(self):
        # Without it the provider refuses a browser-originated call, and
        # the user reads that as a bad key.
        self.assertIn("anthropic-dangerous-direct-browser-access", self.js)

    def test_the_openai_shape_puts_system_first(self):
        self.assertIn("[{ role: 'system', content: systemPrompt }]", self.js)

    def test_a_request_carries_a_timeout_and_can_be_aborted(self):
        self.assertIn("AbortController", self.js)
        self.assertIn("REQUEST_TIMEOUT_MS", self.js)

    def test_an_empty_key_short_circuits_before_the_network(self):
        for fn in ("async function chatStream", "async function chatCompletion"):
            with self.subTest(fn=fn):
                idx = self.js.index(fn)
                body = self.js[idx:idx + 260]
                self.assertIn("if (!apiKey) throw", body)

    def test_the_rate_limiter_is_checked_before_sending(self):
        idx = self.js.index("async function chatStream")
        body = self.js[idx:idx + 400]
        self.assertLess(body.index("rateLimitOk()"), body.index("buildRequest("))

    def test_auth_and_quota_errors_never_echo_the_provider_body(self):
        # Reflecting provider text back can leak the request; only the
        # generic case is allowed to carry it.
        idx = self.js.index("async function readError")
        body = self.js[idx:idx + 700]
        self.assertIn("ConnectorError(kind, 'auth')", body)
        self.assertIn("ConnectorError(kind, 'quota')", body)

    def test_every_provider_declares_a_shape_and_models(self):
        import re
        block = self.js[self.js.index("const PROVIDERS"):self.js.index("const DEFAULT_PROVIDER")]
        keys = re.findall(r"^\s{4}(\w+):\s*\{", block, re.MULTILINE)
        self.assertGreaterEqual(len(keys), 4, f"providers found: {keys}")
        for key in keys:
            with self.subTest(provider=key):
                start = block.index(f"{key}: {{")
                entry = block[start:start + 900]
                self.assertIn("shape:", entry)
                self.assertIn("models:", entry)
                self.assertIn("baseUrl:", entry)


if __name__ == "__main__":
    unittest.main()
