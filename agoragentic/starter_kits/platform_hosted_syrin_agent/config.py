"""Configuration helpers for the platform-hosted Syrin starter kit."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Mapping

from agoragentic.starter_kits.platform_hosted_syrin_agent.hosted_provider import normalize_provider_name

SMOKE_CHECKS = ("health", "ready", "describe")
_TRUE_VALUES = {"1", "true", "yes", "on"}
PREVIEW_PROMPT_TAG = "platform-preview-only"
PREVIEW_PROMPT_INSTRUCTION = (
    "Do not begin cloud provisioning, billing, listing activation, or secret injection "
    "until reviewed execution claims are approved."
)
LIVE_PROMPT_TAG = "platform-live-enabled"
LIVE_PROMPT_INSTRUCTION = (
    "Live hosted actions are allowed only when provider wiring, billing approval, and "
    "operator review are all explicit."
)


def _env_flag(value: str | None, default: bool = False) -> bool:
    """Parse a conventional truthy environment flag."""
    if value is None:
        return default
    return value.strip().lower() in _TRUE_VALUES


def _env_float(value: str | None, default: float) -> float:
    """Parse a float environment variable with a safe default."""
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) and parsed >= 0 else 0.0


@dataclass(frozen=True)
class PlatformHostedStarterProfile:
    """Runtime profile for the platform-hosted Syrin starter kit."""

    provider_name: str
    region: str
    live_enabled: bool
    runtime_bridge_wired: bool
    billing_authorized: bool
    operator_approved: bool
    model_name: str
    max_budget_usd: float
    service_url: str | None = None
    smoke_checks: tuple[str, ...] = SMOKE_CHECKS
    hosting_target: str = "platform_hosted_syrin"


def build_runtime_profile(env: Mapping[str, str] | None = None) -> PlatformHostedStarterProfile:
    """Build a platform-hosted profile from environment variables."""
    source = os.environ if env is None else env
    provider_name = normalize_provider_name(source.get("PLATFORM_HOSTED_PROVIDER") or "simulated")
    service_url = (source.get("PLATFORM_HOSTED_SERVICE_URL") or "").strip() or None
    return PlatformHostedStarterProfile(
        provider_name=provider_name or "simulated_runtime",
        region=(source.get("PLATFORM_HOSTED_REGION") or "us-east-1").strip() or "us-east-1",
        live_enabled=_env_flag(source.get("AGORAGENTIC_RUN_LIVE"), default=False),
        runtime_bridge_wired=_env_flag(source.get("PLATFORM_HOSTED_RUNTIME_BRIDGE_WIRED"), default=False),
        billing_authorized=_env_flag(source.get("PLATFORM_HOSTED_BILLING_AUTHORIZED"), default=False),
        operator_approved=_env_flag(source.get("PLATFORM_HOSTED_OPERATOR_APPROVED"), default=False),
        model_name=(source.get("SYRIN_MODEL_NAME") or "gpt-4o-mini").strip() or "gpt-4o-mini",
        max_budget_usd=_env_float(source.get("SYRIN_MAX_BUDGET_USD"), 1.0),
        service_url=service_url,
    )


def build_system_prompt(profile: PlatformHostedStarterProfile) -> str:
    """Return the control-plane prompt for platform-hosted deployment work."""
    mode_line = (
        f"Execution mode: {LIVE_PROMPT_TAG}. {LIVE_PROMPT_INSTRUCTION}"
        if profile.live_enabled
        else f"Execution mode: {PREVIEW_PROMPT_TAG}. {PREVIEW_PROMPT_INSTRUCTION}"
    )
    return "\n".join(
        [
            "You are a platform-hosted Agoragentic x Syrin deployment planner.",
            mode_line,
            "Prefer provider plan previews before any hosted control-plane action.",
            "Use reviewed execution claims for provision, smoke, activate, and self-serve launch steps.",
            "Reject inline secrets and rely on vault handoff references only.",
            "Do not claim runtime trust until smoke results and intent reconciliation are attached.",
        ]
    )


def build_startup_notes(profile: PlatformHostedStarterProfile) -> tuple[str, ...]:
    """Describe the current platform-hosted runtime state for operator visibility."""
    notes = [
        (
            "Mode: live-enabled. Hosted actions still require reviewed execution claims."
            if profile.live_enabled
            else "Mode: preview-only. Hosted actions will remain contract previews until AGORAGENTIC_RUN_LIVE=1."
        ),
        f"Provider lane: {profile.provider_name} in {profile.region}",
        f"Budget cap: ${profile.max_budget_usd:.2f}",
        f"Runtime bridge wired: {'yes' if profile.runtime_bridge_wired else 'no'}",
        f"Billing authorized: {'yes' if profile.billing_authorized else 'no'}",
        f"Operator approved: {'yes' if profile.operator_approved else 'no'}",
    ]
    if profile.service_url:
        notes.append(f"Attached service URL: {profile.service_url}")
    else:
        notes.append("Attached service URL: none yet; smoke and activation remain gated.")
    return tuple(notes)
