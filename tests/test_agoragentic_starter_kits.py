"""Regression coverage for deployable Agoragentic starter kits."""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STARTER_KITS = ROOT / "agoragentic" / "starter_kits"
HOSTED_KIT = STARTER_KITS / "hosted_syrin_agent"
PLATFORM_HOSTED_KIT = STARTER_KITS / "platform_hosted_syrin_agent"
CONFIG_PATH = HOSTED_KIT / "config.py"


def _load_module(name: str, path: Path):
    """Import a Python file directly from its path."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AgoragenticStarterKitTests(unittest.TestCase):
    """Regression coverage for the deployable hosted Syrin starter kit."""

    @classmethod
    def setUpClass(cls):
        """Load the starter-kit config module once for the test class."""
        cls.config = _load_module("hosted_syrin_agent_config", CONFIG_PATH)

    def test_runtime_profile_defaults_to_preview_first(self):
        """The starter kit should be safe by default when env vars are absent."""
        profile = self.config.build_runtime_profile({})

        self.assertEqual(profile.port, 8000)
        self.assertFalse(profile.live_enabled)
        self.assertTrue(profile.enable_playground)
        self.assertTrue(profile.debug)
        self.assertEqual(profile.max_budget_usd, 1.0)
        self.assertEqual(profile.smoke_paths, ("/health", "/ready", "/describe"))

    def test_runtime_profile_accepts_explicit_overrides(self):
        """The starter kit should honor operator-supplied runtime overrides."""
        profile = self.config.build_runtime_profile(
            {
                "HOSTED_SYRIN_PORT": "9001",
                "AGORAGENTIC_RUN_LIVE": "true",
                "SYRIN_ENABLE_PLAYGROUND": "0",
                "SYRIN_DEBUG": "off",
                "SYRIN_MODEL_NAME": "gpt-4.1-mini",
                "SYRIN_MAX_BUDGET_USD": "2.5",
                "AGORAGENTIC_BASE_URL": "https://preview.example.com/",
            }
        )

        self.assertEqual(profile.port, 9001)
        self.assertTrue(profile.live_enabled)
        self.assertFalse(profile.enable_playground)
        self.assertFalse(profile.debug)
        self.assertEqual(profile.model_name, "gpt-4.1-mini")
        self.assertEqual(profile.max_budget_usd, 2.5)
        self.assertEqual(profile.agoragentic_base_url, "https://preview.example.com")

    def test_runtime_profile_clamps_negative_values_fail_closed(self):
        """Explicit negative port and budget values should not silently widen access."""
        profile = self.config.build_runtime_profile(
            {
                "HOSTED_SYRIN_PORT": "-9",
                "SYRIN_MAX_BUDGET_USD": "-3.0",
            }
        )

        self.assertEqual(profile.port, 8000)
        self.assertEqual(profile.max_budget_usd, 0.0)

    def test_system_prompt_keeps_preview_first_contract(self):
        """The hosted prompt should make spend and mutation gates explicit."""
        preview_prompt = self.config.build_system_prompt(live_enabled=False)
        live_prompt = self.config.build_system_prompt(live_enabled=True)

        self.assertIn(self.config.PREVIEW_PROMPT_TAG, preview_prompt)
        self.assertIn(self.config.PREVIEW_PROMPT_INSTRUCTION, preview_prompt)
        self.assertIn(self.config.LIVE_PROMPT_TAG, live_prompt)
        self.assertIn(self.config.LIVE_PROMPT_INSTRUCTION, live_prompt)

    def test_startup_notes_surface_missing_credentials(self):
        """Operators should get explicit startup notes about missing keys."""
        profile = self.config.build_runtime_profile({})
        notes = self.config.build_startup_notes(
            profile,
            {"OPENAI_API_KEY": "", "AGORAGENTIC_API_KEY": ""},
        )

        self.assertTrue(any("preview-only" in note for note in notes))
        self.assertTrue(any("Model.mock()" in note for note in notes))
        self.assertTrue(any("marketplace tool calls will fail" in note for note in notes))

    def test_hosted_starter_kit_files_exist(self):
        """The hosted starter kit should ship the expected deployable assets."""
        required_files = (
            "__init__.py",
            ".env.example",
            "README.md",
            "Dockerfile",
            "agent.py",
            "config.py",
            "docker-compose.yml",
            "requirements.txt",
            "serve.py",
            "smoke_test.py",
            "tracing.py",
            "agent_os_prompt.py",
        )

        for filename in required_files:
            with self.subTest(filename=filename):
                self.assertTrue((HOSTED_KIT / filename).exists(), msg=f"missing {filename}")

    def test_platform_hosted_starter_kit_files_exist(self):
        """The platform-hosted starter kit should ship the expected control-plane assets."""
        required_files = (
            "__init__.py",
            ".env.example",
            "README.md",
            "agent_os_prompt.py",
            "config.py",
            "deployment.py",
            "hosted_provider.py",
            "launch_request.py",
            "reviewed_executor.py",
        )

        for filename in required_files:
            with self.subTest(filename=filename):
                self.assertTrue((PLATFORM_HOSTED_KIT / filename).exists(), msg=f"missing {filename}")

    def test_docs_reference_the_hosted_starter_kit(self):
        """Top-level docs should point users toward the deployable starter kit."""
        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        integration_readme = (ROOT / "agoragentic" / "README.md").read_text(encoding="utf-8")
        deployment_guide = (ROOT / "agoragentic" / "SANDBOX_AND_DEPLOYMENT.md").read_text(encoding="utf-8")
        starter_index = (STARTER_KITS / "README.md").read_text(encoding="utf-8")

        self.assertIn("deployable hosted agent starter kit", root_readme)
        self.assertIn("platform-hosted starter kit", root_readme)
        self.assertIn("starter_kits/hosted_syrin_agent/README.md", integration_readme)
        self.assertIn("starter_kits/platform_hosted_syrin_agent/README.md", integration_readme)
        self.assertIn("AGENT_LIGHTNING_BRIDGE.md", integration_readme)
        self.assertIn("control plane", integration_readme)
        self.assertIn("hosted_syrin_agent", starter_index)
        self.assertIn("platform_hosted_syrin_agent", starter_index)
        self.assertIn("Agent Lightning-compatible", starter_index)
        self.assertIn("launch_request.py", deployment_guide)
        self.assertIn("smoke_test.py", deployment_guide)


if __name__ == "__main__":
    unittest.main()
