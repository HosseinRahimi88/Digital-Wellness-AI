"""connector.js provider catalogue - HANDOFF.md item 1.

Was: OpenAI (3 models), Anthropic (3), Groq (1 model, no tiers), OpenRouter
(2 models). The brief asks for Gemini and Grok added AND every existing
provider filled out to a full weak/mid/strong range, not just the two new
ones. Runs the real connector.js under node (see
tests/test_badge_service.py for the established pattern) so this fails if
the actual file regresses, not a Python copy of its data.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONNECTOR = REPO_ROOT / "frontend" / "assets" / "js" / "connector.js"


class TestConnectorProviders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node is not available")
        script = (
            "const store = {};"
            "globalThis.localStorage = {"
            "  getItem: (k) => (k in store ? store[k] : null),"
            "  setItem: (k, v) => { store[k] = v; },"
            "};"
            "globalThis.window = {};"
            f"require({json.dumps(str(CONNECTOR))});"
            "const C = window.DWConnector;"
            "const out = {};"
            "for (const p of C.providerList()) {"
            "  C.setProviderKey(p.key);"
            "  out[p.key] = { freeform: p.freeform, shape: C.PROVIDERS[p.key].shape,"
            "    baseUrl: C.PROVIDERS[p.key].baseUrl, models: C.modelList() };"
            "}"
            "console.log(JSON.stringify(out));"
        )
        result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise AssertionError("connector.js failed to load: " + result.stderr)
        cls.providers = json.loads(result.stdout)

    def test_gemini_and_grok_are_present(self):
        self.assertIn("gemini", self.providers)
        self.assertIn("grok", self.providers)

    def test_gemini_and_grok_speak_a_supported_request_shape(self):
        for key in ("gemini", "grok"):
            with self.subTest(provider=key):
                self.assertIn(self.providers[key]["shape"], ("openai", "anthropic"))
                self.assertTrue(self.providers[key]["baseUrl"].startswith("https://"))

    def test_every_non_freeform_provider_has_a_weak_mid_strong_range(self):
        for key, info in self.providers.items():
            if info["freeform"]:
                continue
            with self.subTest(provider=key):
                self.assertGreaterEqual(
                    len(info["models"]), 3,
                    f"{key} has only {len(info['models'])} model(s) - "
                    "expected at least a weak/mid/strong triplet",
                )
                tiers = [m["tier"] for m in info["models"]]
                self.assertEqual(
                    len(tiers), len(set(tiers)),
                    f"{key} has duplicate tier labels: {tiers}",
                )
                ids = [m["id"] for m in info["models"]]
                self.assertEqual(len(ids), len(set(ids)), f"{key} has duplicate model ids: {ids}")

    def test_no_model_id_or_label_is_empty(self):
        for key, info in self.providers.items():
            for model in info["models"]:
                with self.subTest(provider=key, model=model.get("id")):
                    self.assertTrue(model.get("id"))
                    self.assertTrue(model.get("label"))
                    self.assertTrue(model.get("tier"))


if __name__ == "__main__":
    unittest.main()
