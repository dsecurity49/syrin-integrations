"""Preview-first platform-hosted Syrin starter kit."""

from .agent_os_prompt import build_agent_os_implementation_prompt
from .config import (
    PlatformHostedStarterProfile,
    build_runtime_profile,
    build_startup_notes,
    build_system_prompt,
)
from .deployment import (
    HOSTING_TARGET,
    build_live_effects,
    build_platform_hosted_deployment,
    build_smoke_result,
    evaluate_activation_gate,
    latest_fulfillment_state,
)
from .hosted_provider import (
    AwsAppRunnerProviderAdapter,
    HostedGpuBridgeProviderAdapter,
    SimulatedProviderAdapter,
    build_vault_handoff,
    get_provider_adapter,
    normalize_provider_name,
)
from .reviewed_executor import (
    HOSTED_CONTROL_PLANE_PAYMENT_RAIL,
    HOSTED_REVIEW_ACTIONS,
    build_hosted_action_state,
    build_hosted_execution_receipt,
    execute_reviewed_hosted_action,
    review_hosted_deployment_action,
)

__all__ = [
    "HOSTED_CONTROL_PLANE_PAYMENT_RAIL",
    "HOSTED_REVIEW_ACTIONS",
    "HOSTING_TARGET",
    "AwsAppRunnerProviderAdapter",
    "HostedGpuBridgeProviderAdapter",
    "PlatformHostedStarterProfile",
    "SimulatedProviderAdapter",
    "build_agent_os_implementation_prompt",
    "build_hosted_action_state",
    "build_hosted_execution_receipt",
    "build_live_effects",
    "build_platform_hosted_deployment",
    "build_runtime_profile",
    "build_smoke_result",
    "build_startup_notes",
    "build_system_prompt",
    "build_vault_handoff",
    "evaluate_activation_gate",
    "execute_reviewed_hosted_action",
    "get_provider_adapter",
    "latest_fulfillment_state",
    "normalize_provider_name",
    "review_hosted_deployment_action",
]
