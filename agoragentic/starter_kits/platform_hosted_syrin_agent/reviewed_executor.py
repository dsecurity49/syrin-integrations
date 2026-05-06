"""Reviewed execution helpers for platform-hosted Syrin starter kits."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

from agoragentic.starter_kits.platform_hosted_syrin_agent.deployment import (
    evaluate_activation_gate,
    latest_fulfillment_state,
)

HOSTED_CONTROL_PLANE_PAYMENT_RAIL = "hosted_control_plane"
HOSTED_REVIEW_ACTIONS = {
    "provision": {
        "action_type": "agent_os.provision",
        "route": "/api/hosting/agent-os/deployments/:id/provision",
        "task": "agent_os_hosted_provision",
    },
    "smoke": {
        "action_type": "agent_os.smoke",
        "route": "/api/hosting/agent-os/deployments/:id/smoke",
        "task": "agent_os_hosted_smoke",
    },
    "activate": {
        "action_type": "agent_os.activate",
        "route": "/api/hosting/agent-os/deployments/:id/activate",
        "task": "agent_os_hosted_activate",
    },
    "self_serve_launch": {
        "action_type": "agent_os.self_serve_launch",
        "route": "/api/hosting/agent-os/deployments/:id/self-serve-launch",
        "task": "agent_os_hosted_self_serve_launch",
    },
}


def _plain_object(value: Any) -> dict[str, Any]:
    """Normalize plain dictionaries and ignore other values."""
    return dict(value) if isinstance(value, Mapping) else {}


def _normalize_bool(value: Any, fallback: bool = False) -> bool:
    """Parse booleans from common shell-style values."""
    if value is None or value == "":
        return fallback
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _stable_json(value: Any) -> str:
    """Build a stable JSON string for hashing review payloads."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _review_hash(value: Any) -> str:
    """Hash a reviewed payload deterministically."""
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def build_hosted_action_state(
    *,
    deployment: Mapping[str, Any],
    body: Mapping[str, Any] | None = None,
    action_key: str,
) -> dict[str, Any]:
    """Capture the current hosted-action gate state for reviewed execution."""
    provider_state = _plain_object(deployment.get("provider_state"))
    activation_gate = evaluate_activation_gate(deployment)
    fulfillment_state = latest_fulfillment_state(deployment)
    service_attached = bool(
        provider_state.get("service_url")
        or provider_state.get("service_arn")
        or provider_state.get("provider_ref")
    )
    body = _plain_object(body)

    return {
        "operator_approved": provider_state.get("operator_approved") is True,
        "runtime_bridge_wired": _normalize_bool(body.get("runtime_bridge_wired"), provider_state.get("runtime_bridge_wired") is True),
        "live_effects_enabled": _normalize_bool(body.get("live_effects_enabled"), provider_state.get("live_effects_enabled") is True),
        "billing_authorized": provider_state.get("billing_authorized") is True,
        "service_attached": service_attached,
        "activation_gate_status": activation_gate["status"],
        "latest_smoke_status": _plain_object(fulfillment_state["latest_smoke_result"]).get("status"),
        "requested_publish_listing": body.get("publish_listing") is True,
        "action_key": action_key,
    }


def review_hosted_deployment_action(
    *,
    deployment: Mapping[str, Any],
    agent_id: str,
    action_key: str,
    body: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Review a hosted action against deterministic platform-hosted gates."""
    action = HOSTED_REVIEW_ACTIONS.get(action_key)
    if not action:
        raise ValueError(f"Unknown hosted reviewed action: {action_key}")

    body = _plain_object(body)
    provider_state = _plain_object(deployment.get("provider_state"))
    provider_name = str(
        body.get("provider_name")
        or body.get("provider")
        or provider_state.get("provider_name")
        or provider_state.get("provider")
        or ""
    ).strip() or None
    state = build_hosted_action_state(deployment=deployment, body=body, action_key=action_key)

    blocked_reasons = []
    if not state["operator_approved"]:
        blocked_reasons.append("Explicit operator approval is required.")
    if not state["runtime_bridge_wired"]:
        blocked_reasons.append("Runtime bridge is not wired.")
    if action_key == "provision" and not state["live_effects_enabled"]:
        blocked_reasons.append("live_effects_enabled is strictly required.")
    if action_key == "provision" and not state["billing_authorized"]:
        blocked_reasons.append("Billing authorization is required before provision.")
    if action_key in {"smoke", "activate", "self_serve_launch"} and not state["service_attached"]:
        blocked_reasons.append("Service attachment is required before smoke or activation.")
    if action_key in {"activate", "self_serve_launch"} and state["activation_gate_status"] != "activation_allowed":
        blocked_reasons.append("Activation gate is not ready.")

    reviewed_payload_hash = _review_hash(body)
    if blocked_reasons:
        return {
            "verdict": "deny",
            "reviewed_payload_hash": reviewed_payload_hash,
            "action_type": action["action_type"],
            "route": action["route"],
            "task": action["task"],
            "policy_context": {
                "deployment_id": deployment["id"],
                "provider_name": provider_name,
                "hosting_target": deployment.get("hosting_target"),
                "hosted_action_state": state,
            },
            "primary_failure": {
                "code": "hosted_action_gate_mismatch",
                "message": blocked_reasons[0],
            },
            "blocked_reasons": blocked_reasons,
            "allowed_execution_claims": None,
        }

    return {
        "verdict": "allow",
        "reviewed_payload_hash": reviewed_payload_hash,
        "action_type": action["action_type"],
        "route": action["route"],
        "task": action["task"],
        "payment_rail": HOSTED_CONTROL_PLANE_PAYMENT_RAIL,
        "policy_context": {
            "deployment_id": deployment["id"],
            "provider_name": provider_name,
            "hosting_target": deployment.get("hosting_target"),
            "hosted_action_state": state,
        },
        "allowed_execution_claims": {
            "route": action["route"],
            "deployment_id": deployment["id"],
            "provider_name": provider_name,
            "hosting_target": deployment.get("hosting_target"),
            "agent_id": agent_id,
            "action_key": action_key,
        },
        "blocked_reasons": [],
        "primary_failure": None,
    }


def build_hosted_execution_receipt(
    *,
    action_key: str,
    decision: Mapping[str, Any],
    deployment: Mapping[str, Any],
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a normalized receipt for reviewed hosted actions."""
    decision = _plain_object(decision)
    result = _plain_object(result)
    deployment_snapshot = _plain_object(result.get("deployment") or deployment)
    provider_state = _plain_object(deployment_snapshot.get("provider_state") or {})
    allowed_claims = _plain_object(decision.get("allowed_execution_claims") or {})
    receipt = {
        "reviewed_payload_hash": decision.get("reviewed_payload_hash"),
        "deployment_id": deployment["id"],
        "provider_name": provider_state.get("provider_name") or allowed_claims.get("provider_name"),
        "payment_rail": HOSTED_CONTROL_PLANE_PAYMENT_RAIL,
        "receipt_required": False,
    }
    if action_key == "provision":
        receipt["status"] = _plain_object(result.get("provision")).get("status") or "provisioning_started"
    elif action_key == "smoke":
        receipt["status"] = _plain_object(result.get("smoke_result")).get("status") or "unverifiable"
    else:
        receipt["status"] = _plain_object(result.get("activation")).get("status") or "activation_blocked_pending_runtime_proof"
    return receipt


def execute_reviewed_hosted_action(
    *,
    deployment: Mapping[str, Any],
    agent_id: str,
    action_key: str,
    body: Mapping[str, Any] | None = None,
    execute: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    """Execute a hosted action only when reviewed gates allow it."""
    if not callable(execute):
        raise ValueError(f"Hosted reviewed action {action_key} requires an execute function.")

    decision = review_hosted_deployment_action(
        deployment=deployment,
        agent_id=agent_id,
        action_key=action_key,
        body=body,
    )
    if decision["verdict"] != "allow":
        return {
            "allowed": False,
            "decision": decision,
            "receipt": None,
            "result": None,
        }

    result = execute({"decision": decision})
    receipt = build_hosted_execution_receipt(
        action_key=action_key,
        decision=decision,
        deployment=deployment,
        result=result,
    )
    return {
        "allowed": True,
        "decision": decision,
        "receipt": receipt,
        "result": result,
    }
