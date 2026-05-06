"""Regression coverage for the platform-hosted Syrin starter kit."""

import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PlatformHostedStarterKitTests(unittest.TestCase):
    """Coverage for platform-hosted provider previews and reviewed execution."""

    @classmethod
    def setUpClass(cls):
        """Load the platform-hosted modules once for the test class."""
        cls.config = importlib.import_module("agoragentic.starter_kits.platform_hosted_syrin_agent.config")
        cls.deployment = importlib.import_module("agoragentic.starter_kits.platform_hosted_syrin_agent.deployment")
        cls.provider = importlib.import_module("agoragentic.starter_kits.platform_hosted_syrin_agent.hosted_provider")
        cls.executor = importlib.import_module("agoragentic.starter_kits.platform_hosted_syrin_agent.reviewed_executor")
        cls.prompt = importlib.import_module("agoragentic.starter_kits.platform_hosted_syrin_agent.agent_os_prompt")

    def test_runtime_profile_defaults_to_preview_first(self):
        """The platform-hosted starter kit should default to simulated preview mode."""
        profile = self.config.build_runtime_profile({})

        self.assertEqual(profile.provider_name, "simulated_runtime")
        self.assertEqual(profile.region, "us-east-1")
        self.assertFalse(profile.live_enabled)
        self.assertFalse(profile.runtime_bridge_wired)
        self.assertFalse(profile.billing_authorized)
        self.assertFalse(profile.operator_approved)
        self.assertEqual(profile.max_budget_usd, 1.0)

    def test_runtime_profile_rejects_non_finite_budget_values(self):
        """Non-finite budget caps should fail closed instead of widening spend limits."""
        profile = self.config.build_runtime_profile(
            {
                "SYRIN_MAX_BUDGET_USD": "inf",
            }
        )

        self.assertEqual(profile.max_budget_usd, 0.0)

    def test_vault_handoff_rejects_inline_secrets_and_normalizes_aliases(self):
        """Vault handoff should reject inline values and normalize provider aliases."""
        with self.assertRaisesRegex(ValueError, "inline secrets are not allowed"):
            self.provider.build_vault_handoff(
                {
                    "provider": "aws_app_runner",
                    "secrets": [
                        {"type": "inline", "value": "secret_value"},
                    ],
                }
            )

        handoff = self.provider.build_vault_handoff(
            {
                "provider": "aws_app_runner",
                "secrets": [
                    {
                        "type": "reference",
                        "secret_id": "arn:aws:secretsmanager:us-east-2:123456789012:secret:api-key",
                        "env_name": "API_KEY",
                        "provider": "aws_app_runner",
                    },
                    {
                        "type": "reference",
                        "secret_id": "arn:aws:ssm:us-east-2:123456789012:parameter/app/token",
                        "provider": "aws_apprunner",
                    },
                ],
            }
        )

        self.assertEqual(handoff["schema"], "agoragentic.agent-os.vault-handoff.v1")
        self.assertTrue(handoff["credentials_redacted"])
        self.assertEqual(handoff["allowed_boundary"], "adapter_injection_only")
        self.assertEqual(handoff["provider_name"], "aws_apprunner")
        self.assertEqual(handoff["injected_references"][0]["allowed_provider"], "aws_apprunner")
        self.assertEqual(handoff["injected_references"][1]["env_name"], "VAR_REF_02")
        self.assertEqual(handoff["injected_references"][1]["allowed_provider"], "aws_apprunner")
        self.assertEqual(self.provider.normalize_provider_name("vast_ai"), "vast_gpu_worker")

    def test_build_platform_hosted_deployment_shapes_app_runner_repository_preview(self):
        """Repository-backed App Runner plans should keep provider previews deterministic."""
        profile = self.config.build_runtime_profile(
            {
                "PLATFORM_HOSTED_PROVIDER": "aws_app_runner",
                "AGORAGENTIC_RUN_LIVE": "1",
                "PLATFORM_HOSTED_RUNTIME_BRIDGE_WIRED": "1",
                "PLATFORM_HOSTED_BILLING_AUTHORIZED": "1",
                "PLATFORM_HOSTED_OPERATOR_APPROVED": "1",
            }
        )
        deployment = self.deployment.build_platform_hosted_deployment(
            profile=profile,
            agent_name="Hosted OpenClaw Repo",
            source_type="repository",
            source_ref="https://github.com/example/openclaw",
            provider_state={
                "branch": "main",
                "source_directory": "/services/agent",
                "app_runner_runtime": "python3",
                "build_command": "pip install -r requirements.txt",
                "start_command": "python app.py",
                "runtime_environment_variables": {"LOG_LEVEL": "info"},
            },
            secret_references=[
                {
                    "type": "reference",
                    "env_name": "API_KEY",
                    "secret_id": "arn:aws:secretsmanager:us-east-2:123456789012:secret:openclaw-api-key",
                    "provider": "aws_apprunner",
                }
            ],
        )

        preview = deployment["deployment_plan"]["provider_preview"]
        secret_preview = deployment["deployment_plan"]["secret_injection_preview"]

        self.assertEqual(deployment["hosting_target"], "platform_hosted_syrin")
        self.assertEqual(preview["status"], "provision_preview_ready")
        self.assertEqual(preview["provider"], "aws_apprunner")
        self.assertEqual(preview["used_action"], "CreateService")
        self.assertEqual(preview["source_configuration"]["code_repository"]["repository_url"], "https://github.com/example/openclaw")
        self.assertEqual(preview["source_configuration"]["code_repository"]["source_directory"], "/services/agent")
        self.assertEqual(preview["source_configuration"]["code_repository"]["runtime"], "PYTHON_3")
        self.assertEqual(secret_preview["runtime_environment_secrets"]["API_KEY"], "arn:aws:secretsmanager:us-east-2:123456789012:secret:openclaw-api-key")

    def test_build_platform_hosted_deployment_filters_gate_evidence_from_provider_state(self):
        """Caller-supplied provider metadata must not open reviewed execution gates."""
        profile = self.config.build_runtime_profile(
            {
                "PLATFORM_HOSTED_PROVIDER": "aws_apprunner",
            }
        )
        deployment = self.deployment.build_platform_hosted_deployment(
            profile=profile,
            agent_name="Hosted Filter Check",
            source_type="repository",
            source_ref="https://github.com/example/openclaw",
            provider_state={
                "operator_approved": True,
                "runtime_bridge_wired": True,
                "live_effects_enabled": True,
                "billing_authorized": True,
                "service_url": "https://should-not-attach.example.com",
                "provider_ref": "svc_123",
                "provider_name": "vast_gpu_worker",
                "branch": "main",
            },
        )

        provider_state = deployment["provider_state"]
        self.assertEqual(provider_state["provider_name"], "aws_apprunner")
        self.assertFalse(provider_state["operator_approved"])
        self.assertFalse(provider_state["runtime_bridge_wired"])
        self.assertFalse(provider_state["live_effects_enabled"])
        self.assertFalse(provider_state["billing_authorized"])
        self.assertNotIn("service_url", provider_state)
        self.assertNotIn("provider_ref", provider_state)
        self.assertEqual(provider_state["branch"], "main")

    def test_smoke_result_and_activation_gate_keep_provider_metadata(self):
        """Smoke artifacts and activation gating should preserve hosted evidence."""
        deployment = {
            "id": "dep_123",
            "provider_state": {"provider_name": "aws_apprunner"},
            "deployment_plan": {
                "fulfillment_reviews": [{"status": "operator_review_approved"}],
                "smoke_results": [{"status": "passed"}],
                "intent_reconciliations": [{"verdict": "aligned"}],
            },
        }
        smoke = self.deployment.build_smoke_result(
            deployment=deployment,
            body={"requested_checks": ["health"]},
            adapter_result={
                "status": "passed",
                "spend_usdc": 0.1,
                "provider": "aws_apprunner",
                "latency_ms": 211,
                "live_effects": {"external_calls_made": True},
            },
        )
        gate = self.deployment.evaluate_activation_gate(deployment)

        self.assertEqual(smoke["schema"], "agoragentic.agent-os.smoke-result.v1")
        self.assertEqual(smoke["deployment_id"], "dep_123")
        self.assertEqual(smoke["status"], "passed")
        self.assertIsNone(smoke["failure_class"])
        self.assertEqual(smoke["provider"], "aws_apprunner")
        self.assertEqual(smoke["latency_ms"], 211)
        self.assertEqual(smoke["requested_checks"], ["health"])
        self.assertTrue(smoke["live_effects"]["external_calls_made"])
        self.assertEqual(gate["status"], "activation_allowed")
        self.assertEqual(gate["blocked_reasons"], [])

    def test_smoke_result_fails_closed_for_invalid_spend_metadata(self):
        """Malformed spend metadata should not raise or widen reported cost."""
        deployment = {
            "id": "dep_spend",
            "provider_state": {"provider_name": "aws_apprunner"},
        }

        invalid = self.deployment.build_smoke_result(
            deployment=deployment,
            adapter_result={"status": "passed", "spend_usdc": "n/a"},
        )
        infinite = self.deployment.build_smoke_result(
            deployment=deployment,
            adapter_result={"status": "passed", "spend_usdc": "inf"},
        )

        self.assertEqual(invalid["spend_usdc"], 0.0)
        self.assertEqual(infinite["spend_usdc"], 0.0)

    def test_reviewed_executor_allows_provision_when_gates_are_open(self):
        """Provision review should allow when hosted control-plane gates are explicit."""
        decision = self.executor.review_hosted_deployment_action(
            deployment={
                "id": "dep_hosted_1",
                "hosting_target": "platform_hosted_syrin",
                "provider_state": {
                    "provider_name": "aws_apprunner",
                    "operator_approved": True,
                    "runtime_bridge_wired": True,
                    "live_effects_enabled": True,
                    "billing_authorized": True,
                    "service_url": "https://hosted.example.com",
                },
                "deployment_plan": {
                    "fulfillment_reviews": [{"status": "operator_review_approved"}],
                    "smoke_results": [{"status": "passed"}],
                    "intent_reconciliations": [{"verdict": "aligned"}],
                },
            },
            agent_id="agent_hosted_1",
            action_key="provision",
            body={},
        )

        self.assertEqual(decision["verdict"], "allow")
        self.assertEqual(decision["allowed_execution_claims"]["route"], "/api/hosting/agent-os/deployments/:id/provision")
        self.assertEqual(decision["allowed_execution_claims"]["deployment_id"], "dep_hosted_1")
        self.assertEqual(decision["allowed_execution_claims"]["provider_name"], "aws_apprunner")

    def test_reviewed_executor_denies_activate_when_gate_is_not_ready(self):
        """Activation review should deny when intent alignment is missing."""
        decision = self.executor.review_hosted_deployment_action(
            deployment={
                "id": "dep_hosted_2",
                "hosting_target": "platform_hosted_syrin",
                "provider_state": {
                    "provider_name": "aws_apprunner",
                    "operator_approved": True,
                    "runtime_bridge_wired": True,
                    "live_effects_enabled": True,
                    "billing_authorized": True,
                    "service_url": "https://hosted.example.com",
                },
                "deployment_plan": {
                    "fulfillment_reviews": [{"status": "operator_review_approved"}],
                    "smoke_results": [{"status": "passed"}],
                    "intent_reconciliations": [{"verdict": "partial"}],
                },
            },
            agent_id="agent_hosted_1",
            action_key="activate",
            body={"publish_listing": True},
        )

        self.assertEqual(decision["verdict"], "deny")
        self.assertEqual(decision["primary_failure"]["code"], "hosted_action_gate_mismatch")

    def test_execution_receipt_handles_none_snapshots_without_crashing(self):
        """Receipt generation should tolerate explicit None values in executor results and deny decisions."""
        receipt = self.executor.build_hosted_execution_receipt(
            action_key="activate",
            decision={
                "reviewed_payload_hash": "hash_123",
                "allowed_execution_claims": None,
            },
            deployment={
                "id": "dep_hosted_3",
                "provider_state": {"provider_name": "aws_apprunner"},
            },
            result={"deployment": None, "activation": None},
        )

        self.assertEqual(receipt["deployment_id"], "dep_hosted_3")
        self.assertEqual(receipt["provider_name"], "aws_apprunner")
        self.assertEqual(receipt["status"], "activation_blocked_pending_runtime_proof")

    def test_app_runner_secret_injection_rejects_cross_provider_refs(self):
        """Mismatched secret-provider refs should fail loudly instead of being skipped."""
        adapter = self.provider.AwsAppRunnerProviderAdapter()
        handoff = self.provider.build_vault_handoff(
            {
                "provider_name": "aws_apprunner",
                "secrets": [
                    {
                        "secret_id": "arn:aws:secretsmanager:us-east-2:123456789012:secret:api-key",
                        "env_name": "API_KEY",
                    },
                    {
                        "secret_id": "arn:aws:secretsmanager:us-east-2:123456789012:secret:wrong-provider",
                        "env_name": "OTHER_KEY",
                        "provider": "simulated_runtime",
                    },
                ],
            }
        )

        with self.assertRaisesRegex(ValueError, "different provider"):
            adapter.inject_secrets({"provider_state": {}}, handoff)

    def test_service_name_normalization_strips_trailing_hyphen_after_truncation(self):
        """Provider-friendly service names should not end with a dangling hyphen after truncation."""
        service_name = self.provider._normalize_service_name("Syrin Hosted Some Very Long Agent Name -")

        self.assertFalse(service_name.endswith("-"))

    def test_agent_os_prompt_preserves_reviewed_boundary(self):
        """The platform prompt should keep provider previews and reviewed execution separate."""
        prompt = self.prompt.build_agent_os_implementation_prompt()

        self.assertIn("preview-first platform-hosted", prompt)
        self.assertIn("reviewed execution", prompt)
        self.assertIn("do not start automatic cloud provisioning", prompt)
        self.assertIn("do not imply this repository replaces Syrin Nexus or Syrin CLI", prompt)
        self.assertIn("launch_request.py", prompt)


if __name__ == "__main__":
    unittest.main()
