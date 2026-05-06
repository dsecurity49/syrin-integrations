"""Deployment-plan helpers for platform-hosted Syrin starter kits."""

from __future__ import annotations

import math
import uuid
from typing import Any, Mapping

from agoragentic.starter_kits.platform_hosted_syrin_agent.config import PlatformHostedStarterProfile
from agoragentic.starter_kits.platform_hosted_syrin_agent.hosted_provider import (
    build_vault_handoff,
    get_provider_adapter,
    normalize_provider_name,
)

HOSTING_TARGET = "platform_hosted_syrin"


def _new_id(prefix: str) -> str:
    """Build a short identifier for deployment artifacts."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _latest(entries: list[Mapping[str, Any]] | None) -> Mapping[str, Any] | None:
    """Return the most recent entry from a list-like history."""
    if not isinstance(entries, list) or not entries:
        return None
    entry = entries[-1]
    return entry if isinstance(entry, Mapping) else None


def _plain_object(value: Any) -> dict[str, Any]:
    """Normalize plain dictionaries and ignore other values."""
    return dict(value) if isinstance(value, Mapping) else {}


def _non_negative_finite_float(value: Any, default: float = 0.0) -> float:
    """Normalize numeric metadata without accepting malformed or non-finite values."""
    try:
        parsed = float(str(value).strip())
    except (AttributeError, TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) and parsed >= 0 else default


def build_live_effects(overrides: Mapping[str, Any] | None = None) -> dict[str, bool]:
    """Return a normalized live-effects report."""
    effects = _plain_object(overrides)
    return {
        "cloud_provisioning_started": effects.get("cloud_provisioning_started") is True,
        "model_inference_started": effects.get("model_inference_started") is True,
        "wallet_or_billing_started": effects.get("wallet_or_billing_started") is True,
        "marketplace_listing_published": effects.get("marketplace_listing_published") is True,
        "code_mutation_started": effects.get("code_mutation_started") is True,
        "external_calls_made": effects.get("external_calls_made") is True,
    }


def latest_fulfillment_state(deployment: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the latest fulfillment evidence attached to a deployment."""
    deployment_plan = _plain_object((deployment or {}).get("deployment_plan"))
    return {
        "latest_fulfillment_review": _latest(deployment_plan.get("fulfillment_reviews")),
        "latest_smoke_result": _latest(deployment_plan.get("smoke_results")),
        "latest_intent_reconciliation": _latest(deployment_plan.get("intent_reconciliations")),
    }


def evaluate_activation_gate(deployment: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Decide whether a hosted deployment is ready for marketplace activation."""
    latest_state = latest_fulfillment_state(deployment)
    blocked_reasons = []

    if (latest_state["latest_fulfillment_review"] or {}).get("status") != "operator_review_approved":
        blocked_reasons.append("Fulfillment review missing or not approved")
    if (latest_state["latest_smoke_result"] or {}).get("status") != "passed":
        blocked_reasons.append("Smoke result missing or not passed")
    if (latest_state["latest_intent_reconciliation"] or {}).get("verdict") != "aligned":
        blocked_reasons.append("Intent reconciliation missing or not aligned")

    return {
        "status": "activation_allowed" if not blocked_reasons else "activation_blocked",
        "blocked_reasons": blocked_reasons,
        "latest_state": latest_state,
    }


def build_smoke_result(
    *,
    deployment: Mapping[str, Any],
    body: Mapping[str, Any] | None = None,
    adapter_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a normalized smoke-result artifact."""
    payload = _plain_object(body)
    result = _plain_object(adapter_result)
    status = str(result.get("status") or "unverifiable")
    failure_class = None if status == "passed" else str(result.get("failure_class") or "runtime_unverified")
    provider_state = _plain_object(deployment.get("provider_state"))
    requested_checks = payload.get("requested_checks")
    if not isinstance(requested_checks, list):
        requested_checks = []
    return {
        "schema": "agoragentic.agent-os.smoke-result.v1",
        "id": _new_id("smk"),
        "deployment_id": deployment["id"],
        "status": status,
        "failure_class": failure_class,
        "provider": result.get("provider") or provider_state.get("provider_name"),
        "latency_ms": result.get("latency_ms"),
        "spend_usdc": _non_negative_finite_float(result.get("spend_usdc"), 0.0),
        "requested_checks": [str(check) for check in requested_checks],
        "live_effects": build_live_effects(result.get("live_effects")),
        "evidence_refs": [str(ref) for ref in result.get("evidence_refs") or []],
        "runtime_trust": result.get("runtime_trust"),
    }


def build_platform_hosted_deployment(
    *,
    profile: PlatformHostedStarterProfile,
    agent_name: str,
    source_type: str,
    source_ref: str,
    goal: str | None = None,
    publish_listing: bool = False,
    provider_state: Mapping[str, Any] | None = None,
    secret_references: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a preview-first platform-hosted deployment record and provider preview."""
    deployment_id = _new_id("dep")
    agent_id = _new_id("agt")
    normalized_provider = normalize_provider_name(profile.provider_name) or "simulated_runtime"
    state = {
        "provider_name": normalized_provider,
        "operator_approved": profile.operator_approved,
        "runtime_bridge_wired": profile.runtime_bridge_wired,
        "live_effects_enabled": profile.live_enabled,
        "billing_authorized": profile.billing_authorized,
        "region": profile.region,
    }
    reserved_provider_state_keys = {
        "billing_authorized",
        "live_effects_enabled",
        "operator_approved",
        "provider",
        "provider_name",
        "provider_ref",
        "runtime_bridge_wired",
        "service_arn",
        "service_url",
    }
    provider_overrides = {
        key: value
        for key, value in _plain_object(provider_state).items()
        if key not in reserved_provider_state_keys
    }
    state.update(provider_overrides)
    if profile.service_url and "service_url" not in state:
        state["service_url"] = profile.service_url

    deployment = {
        "schema": "agoragentic.agent-os.deployment-plan.v1",
        "id": deployment_id,
        "agent_id": agent_id,
        "name": agent_name,
        "hosting_target": HOSTING_TARGET,
        "source_type": source_type,
        "source_ref": source_ref,
        "preview_only": not profile.live_enabled,
        "provider_state": state,
        "deployment_plan": {
            "goal_contract": {
                "primary_goal": goal or "Launch a platform-hosted Syrin agent without bypassing review gates.",
                "publish_listing": publish_listing,
                "preview_only": not profile.live_enabled,
            },
            "launch_contract": {
                "provider_name": normalized_provider,
                "runtime_lane": {
                    "id": "dedicated_gpu_cluster" if normalized_provider == "vast_gpu_worker" else "managed_http_runtime"
                },
                "source_type": source_type,
                "source_ref": source_ref,
                "publish_listing": publish_listing,
            },
            "phases": [
                {"id": "validate_source", "description": "Confirm source ref and runtime contract before hosted action review."},
                {"id": "prepare_provider", "description": "Normalize provider inputs and validate hosted-provider compatibility."},
                {"id": "preview_provision", "description": "Shape a provider launch request without beginning cloud provisioning."},
                {"id": "smoke_gate", "description": "Require smoke evidence before claiming runtime trust."},
                {"id": "activation_gate", "description": "Require approved review, smoke pass, and aligned intent before activation."},
            ],
            "fulfillment_reviews": [],
            "smoke_results": [],
            "intent_reconciliations": [],
        },
    }

    adapter = get_provider_adapter(normalized_provider)
    provider_prepare = adapter.prepare(deployment)
    secret_handoff = None
    secret_injection_preview = {"status": "no_secret_handoff_requested", "accepted_references": 0}
    if secret_references:
        secret_handoff = build_vault_handoff(
            {
                "provider_name": normalized_provider,
                "secrets": secret_references,
            }
        )
        secret_injection_preview = adapter.inject_secrets(deployment, secret_handoff)
    provider_preview = adapter.provision(
        deployment,
        {
            "vault_handoff": secret_handoff,
            "secret_injection_result": secret_injection_preview,
        },
    )

    deployment["deployment_plan"]["provider_prepare"] = provider_prepare
    deployment["deployment_plan"]["secret_injection_preview"] = secret_injection_preview
    deployment["deployment_plan"]["provider_preview"] = provider_preview
    if secret_handoff:
        deployment["provider_fulfillment"] = {
            "secret_handoff": {
                "schema": secret_handoff["schema"],
                "references": secret_handoff["injected_references"],
            }
        }
    return deployment
