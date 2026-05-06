"""Hosted-provider previews for platform-hosted Syrin starter kits."""

from __future__ import annotations

import re
import uuid
from typing import Any, Mapping

AWS_APPRUNNER_PROVIDER_NAMES = {"aws_apprunner", "aws_app_runner"}
GPU_BRIDGE_PROVIDER_NAMES = {
    "vast_gpu_worker",
    "vast_gpu",
    "vast_ai",
    "gpu_bridge",
    "gpu_worker_bridge",
}
SIMULATED_PROVIDER_NAMES = {"simulated", "simulated_runtime", "noop"}
AWS_SECRET_ARN_PATTERN = re.compile(r"^arn:aws[^:]*:(secretsmanager|ssm):", re.IGNORECASE)
APP_RUNNER_RUNTIME_ALIASES = {
    "python": "PYTHON_3",
    "python3": "PYTHON_3",
    "syrin_python": "PYTHON_3",
    "syrin": "PYTHON_3",
    "node": "NODEJS_22",
    "nodejs": "NODEJS_22",
}


def _plain_object(value: Any) -> dict[str, Any]:
    """Normalize plain dictionaries and ignore other values."""
    return dict(value) if isinstance(value, Mapping) else {}


def _new_id(prefix: str) -> str:
    """Build a short identifier for preview artifacts."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _build_live_effects() -> dict[str, bool]:
    """Return an explicit no-live-effects patch for preview contracts."""
    return {
        "cloud_provisioning_started": False,
        "model_inference_started": False,
        "wallet_or_billing_started": False,
        "marketplace_listing_published": False,
        "code_mutation_started": False,
        "external_calls_made": False,
    }


def normalize_provider_name(provider_name: str | None) -> str:
    """Normalize provider aliases to stable platform-hosted names."""
    normalized = str(provider_name or "").strip().lower()
    if normalized in AWS_APPRUNNER_PROVIDER_NAMES:
        return "aws_apprunner"
    if normalized in GPU_BRIDGE_PROVIDER_NAMES:
        return "vast_gpu_worker"
    if normalized in SIMULATED_PROVIDER_NAMES:
        return "simulated_runtime"
    return normalized


def _normalize_string(value: Any, fallback: str | None = "") -> str | None:
    """Convert an arbitrary value to a trimmed string with fallback."""
    if value is None:
        return fallback
    normalized = str(value).strip()
    return normalized or fallback


def _normalize_env_name(value: Any, fallback_index: int) -> str:
    """Convert arbitrary keys into environment-variable-safe names."""
    raw = str(value or "").strip()
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", raw)
    normalized = re.sub(r"_+", "_", normalized).strip("_").upper()
    if not normalized:
        normalized = f"VAR_REF_{fallback_index + 1:02d}"
    if not re.match(r"^[A-Z_]", normalized):
        normalized = f"VAR_{normalized}"
    return normalized


def _normalize_service_name(value: Any, prefix: str = "agent-os") -> str:
    """Build a provider-friendly service name."""
    raw = str(value or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9-_]+", "-", raw)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    candidate = normalized or f"{prefix}-{uuid.uuid4().hex[:8]}"
    if len(candidate) < 4:
        candidate = f"{prefix}-{candidate}"
    candidate = candidate[:40].strip("-")
    if len(candidate) < 4:
        candidate = f"{prefix}-{uuid.uuid4().hex[:8]}"
        candidate = candidate[:40].strip("-")
    return candidate


def _normalize_app_runner_runtime(value: Any, fallback: str = "PYTHON_3") -> str:
    """Normalize App Runner runtime aliases."""
    raw = str(value or "").strip().lower()
    alias = APP_RUNNER_RUNTIME_ALIASES.get(raw.replace("-", "_"))
    if alias:
        return alias
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip().upper()).strip("_")
    return normalized or fallback


def _normalize_runtime_environment_variables(
    deployment: Mapping[str, Any],
    provider_state: Mapping[str, Any],
) -> dict[str, str]:
    """Build a provider-safe runtime environment map."""
    raw = _plain_object(
        provider_state.get("runtime_environment_variables")
        or provider_state.get("runtime_environment")
        or {}
    )
    env = {}
    for key, value in raw.items():
        if isinstance(value, (str, int, float, bool)):
            env[_normalize_env_name(key, len(env))] = str(value)

    if deployment.get("id"):
        env.setdefault("AGORAGENTIC_DEPLOYMENT_ID", str(deployment["id"]))
    if deployment.get("agent_id"):
        env.setdefault("AGORAGENTIC_AGENT_ID", str(deployment["agent_id"]))
    if deployment.get("hosting_target"):
        env.setdefault("AGORAGENTIC_HOSTING_TARGET", str(deployment["hosting_target"]))
    return env


def _normalize_vault_reference(
    ref: Mapping[str, Any],
    index: int,
    default_provider: str,
) -> dict[str, Any]:
    """Validate and normalize one secret reference for adapter handoff."""
    if not isinstance(ref, Mapping):
        raise ValueError(f"Vault handoff rejected invalid secret references: index {index}: secret reference must be an object")
    if ref.get("type") == "inline" or ref.get("inline") is True or "value" in ref:
        raise ValueError(f"Vault handoff rejected invalid secret references: index {index}: inline secrets are not allowed")

    secret_id = (
        ref.get("secret_id")
        or ref.get("secretId")
        or ref.get("ref")
        or ref.get("vault_ref")
        or ref.get("secret_ref")
        or ref.get("arn")
    )
    if not secret_id:
        raise ValueError(f"Vault handoff rejected invalid secret references: index {index}: secret_id is required")

    return {
        "secret_id": str(secret_id),
        "env_name": _normalize_env_name(ref.get("env_name") or ref.get("envName") or ref.get("name"), index),
        "allowed_provider": normalize_provider_name(
            ref.get("provider") or ref.get("allowed_provider") or default_provider
        ),
        "status": "reference_validated_no_inline_exposure",
    }


def build_vault_handoff(context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a redacted secret-handoff contract for provider adapters."""
    context = _plain_object(context)
    provider_name = normalize_provider_name(context.get("provider_name") or context.get("provider")) or "simulated_runtime"
    secrets = (
        context.get("secret_references")
        or context.get("secret_refs")
        or context.get("vault_references")
        or context.get("secrets")
        or []
    )
    if not isinstance(secrets, list):
        secrets = []

    references = [_normalize_vault_reference(ref, index, provider_name) for index, ref in enumerate(secrets)]
    return {
        "schema": "agoragentic.agent-os.vault-handoff.v1",
        "id": _new_id("vh"),
        "status": "ready_for_adapter",
        "credentials_redacted": True,
        "provider_name": provider_name,
        "injected_references": references,
        "allowed_boundary": "adapter_injection_only",
    }


class BaseHostedProviderAdapter:
    """Base class for provider preview adapters."""

    provider_name = "simulated_runtime"
    supported_source_types: tuple[str, ...] = ()

    def prepare(self, deployment: Mapping[str, Any]) -> dict[str, Any]:
        """Validate basic provider compatibility for a deployment preview."""
        source_type = str(deployment.get("source_type") or "").strip()
        return {
            "status": "prepared",
            "provider": self.provider_name,
            "supported_source": source_type in self.supported_source_types,
        }

    def inject_secrets(
        self,
        _deployment: Mapping[str, Any],
        vault_handoff: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Prepare runtime secret references without exposing inline values."""
        refs = list((vault_handoff or {}).get("injected_references") or [])
        return {
            "status": "secrets_prepared_for_runtime",
            "accepted_references": len(refs),
            "inline_secrets_exposed": 0,
            "runtime_environment_secrets": {},
        }

    def provision(
        self,
        deployment: Mapping[str, Any],
        runtime_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a provider-specific preview for the provision step."""
        raise NotImplementedError

    def smoke_test(self, deployment: Mapping[str, Any]) -> dict[str, Any]:
        """Build a smoke-test preview contract."""
        provider_state = _plain_object(deployment.get("provider_state"))
        service_url = _normalize_string(provider_state.get("service_url"), None)
        return {
            "status": "passed" if service_url else "planned",
            "provider": self.provider_name,
            "runtime_trust": "reachable" if service_url else "unknown",
            "evidence_refs": [f"{service_url}/health"] if service_url else [],
            "latency_ms": 0 if service_url else None,
            "live_effects": _build_live_effects(),
        }

    def activate(self, deployment: Mapping[str, Any]) -> dict[str, Any]:
        """Build a provider activation preview."""
        provider_state = _plain_object(deployment.get("provider_state"))
        service_url = _normalize_string(provider_state.get("service_url"), None)
        return {
            "status": (
                "runtime_ready_for_marketplace_activation"
                if service_url or provider_state.get("provider_ref")
                else "activation_blocked_pending_runtime_proof"
            ),
            "provider": self.provider_name,
            "runtime_trust": "reachable" if service_url else "unknown",
            "service_url": service_url,
            "live_effects": _build_live_effects(),
        }


class SimulatedProviderAdapter(BaseHostedProviderAdapter):
    """No-op adapter for preview-only hosted deployment planning."""

    provider_name = "simulated_runtime"
    supported_source_types = ("repository", "container_image", "runtime_bundle")

    def provision(
        self,
        deployment: Mapping[str, Any],
        runtime_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a deterministic preview contract without live effects."""
        source_type = str(deployment.get("source_type") or "").strip() or "repository"
        source_ref = _normalize_string(deployment.get("source_ref"), "unconfigured-source")
        return {
            "status": "simulated_provisioning_preview",
            "provider": self.provider_name,
            "source_type": source_type,
            "source_ref": source_ref,
            "used_action": "preview_only",
            "preview_only": deployment.get("preview_only", True) is True,
            "live_effects": _build_live_effects(),
            "vault_handoff_attached": bool((runtime_context or {}).get("vault_handoff")),
        }


class AwsAppRunnerProviderAdapter(BaseHostedProviderAdapter):
    """Preview adapter for AWS App Runner-hosted Syrin deployments."""

    provider_name = "aws_apprunner"
    supported_source_types = ("container_image", "repository")

    def inject_secrets(
        self,
        deployment: Mapping[str, Any],
        vault_handoff: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate secret references and convert them into runtime secret mappings."""
        refs = list((vault_handoff or {}).get("injected_references") or [])
        runtime_secrets = {}
        skipped_references = []
        for ref in refs:
            if ref.get("allowed_provider") != self.provider_name:
                skipped_references.append(str(ref.get("env_name") or ref.get("secret_id") or "unknown_secret"))
                continue
            secret_id = str(ref.get("secret_id") or "")
            if not AWS_SECRET_ARN_PATTERN.match(secret_id):
                raise ValueError(
                    f"Provider adapter blocked: {ref.get('env_name') or 'secret'} must reference an AWS Secrets Manager or SSM Parameter Store ARN."
                )
            runtime_secrets[str(ref.get("env_name"))] = secret_id
        if skipped_references:
            raise ValueError(
                "Provider adapter blocked: secret references target a different provider: "
                + ", ".join(skipped_references)
            )

        return {
            "status": "secrets_prepared_for_runtime",
            "accepted_references": len(runtime_secrets),
            "inline_secrets_exposed": 0,
            "runtime_environment_secrets": runtime_secrets,
        }

    def provision(
        self,
        deployment: Mapping[str, Any],
        runtime_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build an App Runner launch preview for repository or image sources."""
        provider_state = _plain_object(deployment.get("provider_state"))
        source_type = str(deployment.get("source_type") or "").strip()
        if source_type not in self.supported_source_types:
            raise ValueError(f"Provider adapter blocked: unsupported source_type {source_type!r} for App Runner.")

        runtime_context = _plain_object(runtime_context)
        runtime_env = _normalize_runtime_environment_variables(deployment, provider_state)
        runtime_secrets = _plain_object((runtime_context.get("secret_injection_result") or {}).get("runtime_environment_secrets"))
        service_name = _normalize_service_name(deployment.get("name") or deployment.get("agent_id"), "syrin-hosted")
        health_path = _normalize_string(provider_state.get("health_check_path"), "/health")
        if not str(health_path).startswith("/"):
            health_path = f"/{health_path}"

        preview = {
            "status": "provision_preview_ready",
            "provider": self.provider_name,
            "region": _normalize_string(provider_state.get("region"), "us-east-1"),
            "service_name": service_name,
            "source_type": source_type,
            "health_check": {"path": health_path, "protocol": "HTTP"},
            "runtime_environment_variables": runtime_env,
            "runtime_environment_secrets": runtime_secrets,
            "used_action": "StartDeployment" if provider_state.get("service_arn") else "CreateService",
            "live_effects": _build_live_effects(),
        }

        if source_type == "container_image":
            image_identifier = _normalize_string(provider_state.get("image_identifier") or deployment.get("source_ref"), None)
            if not image_identifier:
                raise ValueError("Provider adapter blocked: container_image deployments require source_ref or provider_state.image_identifier.")
            preview["source_configuration"] = {
                "image_repository": {
                    "image_identifier": image_identifier,
                    "image_repository_type": (
                        "ECR_PUBLIC" if image_identifier.startswith("public.ecr.aws/") else "ECR"
                    ),
                    "port": _normalize_string(provider_state.get("port"), "8080"),
                    "start_command": _normalize_string(provider_state.get("start_command"), None),
                }
            }
        else:
            preview["source_configuration"] = {
                "code_repository": {
                    "repository_url": _normalize_string(deployment.get("source_ref"), None),
                    "branch": _normalize_string(provider_state.get("branch"), "main"),
                    "source_directory": _normalize_string(provider_state.get("source_directory"), "/"),
                    "configuration_source": _normalize_string(provider_state.get("configuration_source"), "API"),
                    "runtime": _normalize_app_runner_runtime(provider_state.get("app_runner_runtime") or deployment.get("runtime"), "PYTHON_3"),
                    "build_command": _normalize_string(provider_state.get("build_command"), "pip install -r requirements.txt"),
                    "start_command": _normalize_string(provider_state.get("start_command"), "python app.py"),
                }
            }
        return preview


class HostedGpuBridgeProviderAdapter(BaseHostedProviderAdapter):
    """Preview adapter for hosted GPU bridge lanes."""

    provider_name = "vast_gpu_worker"
    supported_source_types = ("repository", "container_image")

    def provision(
        self,
        deployment: Mapping[str, Any],
        runtime_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a GPU-bridge launch preview contract."""
        provider_state = _plain_object(deployment.get("provider_state"))
        source_type = str(deployment.get("source_type") or "").strip()
        if source_type not in self.supported_source_types:
            raise ValueError(f"Provider adapter blocked: unsupported source_type {source_type!r} for GPU bridge.")

        launch_contract = _plain_object(_plain_object(deployment.get("deployment_plan")).get("launch_contract"))
        runtime_env = _normalize_runtime_environment_variables(deployment, provider_state)
        return {
            "status": "gpu_bridge_provision_preview",
            "provider": self.provider_name,
            "runtime_lane": _plain_object(launch_contract.get("runtime_lane")).get("id") or "dedicated_gpu_cluster",
            "source_type": source_type,
            "source_ref": _normalize_string(deployment.get("source_ref"), None),
            "runtime_environment_variables": runtime_env,
            "used_action": "gpu_bridge_provision",
            "service_url": _normalize_string(provider_state.get("service_url"), None),
            "provider_ref": _normalize_string(provider_state.get("provider_ref"), None),
            "live_effects": _build_live_effects(),
            "vault_handoff_attached": bool(_plain_object(runtime_context).get("vault_handoff")),
        }


def get_provider_adapter(provider_name: str | None):
    """Return the preview adapter for a normalized provider name."""
    normalized = normalize_provider_name(provider_name)
    if normalized == "aws_apprunner":
        return AwsAppRunnerProviderAdapter()
    if normalized == "vast_gpu_worker":
        return HostedGpuBridgeProviderAdapter()
    return SimulatedProviderAdapter()
