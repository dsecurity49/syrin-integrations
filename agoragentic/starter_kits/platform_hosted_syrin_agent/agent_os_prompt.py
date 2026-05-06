"""Agent OS prompt builder for the platform-hosted Syrin starter kit."""

from __future__ import annotations

from textwrap import dedent

DEFAULT_AGENT_OS_PLATFORM_OBJECTIVE = (
    "Implement a preview-first platform-hosted Agoragentic x Syrin starter kit "
    "with reviewed execution, provider contracts, secret-handoff boundaries, "
    "and clear control-plane versus execution-plane separation."
)


def build_agent_os_implementation_prompt(
    *,
    objective: str = DEFAULT_AGENT_OS_PLATFORM_OBJECTIVE,
) -> str:
    """Return a copy-paste Agent OS prompt for extending the platform-hosted kit."""
    return dedent(
        f"""
        You are extending the platform-hosted Agoragentic x Syrin starter kit.

        Objective:
        {objective}

        Files in scope:
        - agoragentic/starter_kits/platform_hosted_syrin_agent/config.py
        - agoragentic/starter_kits/platform_hosted_syrin_agent/deployment.py
        - agoragentic/starter_kits/platform_hosted_syrin_agent/hosted_provider.py
        - agoragentic/starter_kits/platform_hosted_syrin_agent/reviewed_executor.py
        - agoragentic/starter_kits/platform_hosted_syrin_agent/launch_request.py
        - agoragentic/starter_kits/platform_hosted_syrin_agent/README.md
        - tests/test_agoragentic_platform_hosted_starter_kit.py

        Required outputs:
        - build provider-specific deployment previews without starting cloud side effects
        - require reviewed execution claims for provision, smoke, activation, and self-serve launch
        - reject inline secrets and only allow redacted vault handoff references
        - keep runtime trust tied to smoke results and aligned intent evidence
        - document self-hosted vs platform-hosted boundaries clearly

        Constraints:
        - do not start automatic cloud provisioning, billing, or listing activation by default
        - do not add cloud SDKs as hard runtime dependencies for this starter kit
        - do not expose secret values in deployment previews or review decisions
        - do not collapse reviewed execution and provider planning into one opaque step
        - do not imply this repository replaces Syrin Nexus or Syrin CLI

        Success criteria:
        - a Syrin user can preview a hosted deployment contract for App Runner, GPU bridge, or simulated lanes
        - reviewed execution returns deterministic allow or deny decisions with explicit claims
        - activation requires review approval, smoke evidence, and aligned intent
        - the docs clearly keep Syrin as the control plane and Agoragentic as the execution plane
        """
    ).strip()
