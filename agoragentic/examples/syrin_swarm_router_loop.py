"""Preview-first Syrin v0.11 swarm router loop for Agoragentic.

Syrin v0.11 adds first-class swarms, shared budget pools, MemoryBus sharing,
A2A routing, runtime budget intervention, and audit hooks. This example keeps
those primitives explicit while using Agoragentic as the marketplace execution
rail.

Safe default:
    The script builds a plan only. It does not call Syrin, spend funds, mutate
    memory, deploy code, or execute paid Agoragentic routes.

Run:
    python agoragentic/examples/syrin_swarm_router_loop.py
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from typing import Any


SENSITIVE_ACTION_TERMS = (
    "execute live",
    "spend",
    "pay",
    "settle",
    "deploy",
    "write memory",
    "store secret",
    "retrieve secret",
    "topup budget",
    "reallocate budget",
)

DEFAULT_AGENT_ROLES = (
    "orchestrator",
    "market_researcher",
    "route_evaluator",
    "advocacy_seller_ops",
)

DEFAULT_MEMORY_TYPES = ("knowledge", "instructions")
BLOCKED_MEMORY_TERMS = ("secret", "private_key", "api_key", "wallet", "payment", "pii")


@dataclass(frozen=True)
class SwarmBudgetPlan:
    """Budget-pool contract for a Syrin swarm using Agoragentic routes."""

    total_budget: float
    per_agent_max: float
    role_allocations: dict[str, float]
    intervention_policy: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe budget plan."""
        return {
            "total_budget": self.total_budget,
            "per_agent_max": self.per_agent_max,
            "role_allocations": self.role_allocations,
            "intervention_policy": self.intervention_policy,
        }


@dataclass(frozen=True)
class SwarmRouterPlan:
    """Complete preview plan for a Syrin swarm backed by Agoragentic."""

    task: str
    topology: str
    budget: SwarmBudgetPlan
    a2a_contracts: list[dict[str, Any]]
    memory_bus_policy: dict[str, Any]
    audit_hooks: list[str]
    approval_report: dict[str, Any]
    execute_payload: dict[str, Any]
    syrin_snippet: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe swarm router plan."""
        return {
            "task": self.task,
            "topology": self.topology,
            "budget": self.budget.as_dict(),
            "a2a_contracts": self.a2a_contracts,
            "memory_bus_policy": self.memory_bus_policy,
            "audit_hooks": self.audit_hooks,
            "approval_report": self.approval_report,
            "execute_payload": self.execute_payload,
            "syrin_snippet": self.syrin_snippet,
        }


def normalize_roles(roles: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """Return unique, non-empty swarm role names with an orchestrator first."""
    raw_roles = roles or DEFAULT_AGENT_ROLES
    normalized: list[str] = []
    for role in raw_roles:
        clean = role.strip().lower().replace(" ", "_")
        if clean and clean not in normalized:
            normalized.append(clean)
    if "orchestrator" not in normalized:
        normalized.insert(0, "orchestrator")
    return tuple(normalized)


def build_budget_plan(
    total_budget: float,
    per_agent_max: float,
    roles: tuple[str, ...] | None = None,
) -> SwarmBudgetPlan:
    """Allocate a shared budget pool without letting any role exceed its cap."""
    active_roles = normalize_roles(roles)
    safe_total = max(0.0, float(total_budget))
    safe_cap = max(0.0, float(per_agent_max))

    if not active_roles or safe_total == 0.0 or safe_cap == 0.0:
        allocations = {role: 0.0 for role in active_roles}
    else:
        equal_share = safe_total / len(active_roles)
        capped_share = min(safe_cap, equal_share)
        floored_share = math.floor(capped_share * 10_000) / 10_000
        allocations = {role: floored_share for role in active_roles}

    return SwarmBudgetPlan(
        total_budget=safe_total,
        per_agent_max=safe_cap,
        role_allocations=allocations,
        intervention_policy={
            "topup_budget_allowed": False,
            "reallocate_budget_allowed": False,
            "requires_orchestrator_or_supervisor": True,
            "requires_human_approval": True,
            "audit_required": True,
        },
    )


def build_a2a_contracts(roles: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Define typed A2A messages for swarm coordination and evidence flow."""
    active_roles = normalize_roles(roles)
    worker_roles = [role for role in active_roles if role != "orchestrator"]
    return [
        {
            "message_type": "RouteRequest",
            "from": "orchestrator",
            "to": worker_roles,
            "required_fields": ["task", "max_cost", "required_evidence"],
            "purpose": "Ask workers to propose or evaluate Agoragentic routes.",
        },
        {
            "message_type": "RouteEvidence",
            "from": worker_roles,
            "to": "orchestrator",
            "required_fields": ["provider_candidates", "risk_notes", "expected_cost"],
            "purpose": "Return marketplace evidence before spend.",
        },
        {
            "message_type": "ApprovalRequired",
            "from": "orchestrator",
            "to": "human_operator",
            "required_fields": ["action", "cost", "risk", "evidence"],
            "purpose": "Interrupt before live spend, deployment, secret access, or budget changes.",
        },
        {
            "message_type": "ExecutionReceipt",
            "from": "agoragentic_execute",
            "to": "memory_bus",
            "required_fields": ["invocation_id", "provider", "cost", "settlement_status"],
            "purpose": "Persist only sanitized receipts and reusable lessons.",
        },
    ]


def memory_bus_policy() -> dict[str, Any]:
    """Return the recommended MemoryBus sharing policy for the swarm."""
    return {
        "allow_types": list(DEFAULT_MEMORY_TYPES),
        "blocked_terms": list(BLOCKED_MEMORY_TERMS),
        "write_requires": ["source_provenance", "receipt_or_trace", "human_review_for_live_actions"],
        "default_action": "quarantine_untrusted_memory",
    }


def is_memory_share_allowed(content: str, memory_type: str = "knowledge") -> bool:
    """Return whether content should be shared on the swarm MemoryBus."""
    normalized_type = memory_type.strip().lower()
    lowered = content.lower()
    return normalized_type in DEFAULT_MEMORY_TYPES and not any(
        blocked in lowered for blocked in BLOCKED_MEMORY_TERMS
    )


def guard_swarm_action(action: str, live_enabled: bool) -> dict[str, Any]:
    """Gate live spend, deployment, secret access, and budget intervention."""
    lowered = action.lower()
    sensitive_terms = [term for term in SENSITIVE_ACTION_TERMS if term in lowered]
    requires_approval = bool(sensitive_terms) or live_enabled
    return {
        "action": action,
        "live_enabled": live_enabled,
        "sensitive_terms": sensitive_terms,
        "requires_approval": requires_approval,
        "allowed": not requires_approval,
    }


def build_execute_payload(
    task: str,
    budget: SwarmBudgetPlan,
    topology: str,
    live_enabled: bool,
) -> dict[str, Any]:
    """Build the preview-first Agoragentic execution payload for the swarm."""
    return {
        "task": task,
        "input": {
            "task": task,
            "syrin_swarm": {
                "version_floor": "0.11.0",
                "topology": topology,
                "roles": list(budget.role_allocations),
                "shared_budget_pool": True,
                "per_agent_max": budget.per_agent_max,
                "a2a_audit_required": True,
                "memory_bus_policy": memory_bus_policy(),
            },
        },
        "constraints": {
            "max_cost": budget.total_budget,
            "per_agent_max": budget.per_agent_max,
            "prefer_execute": True,
            "preview_only": not live_enabled,
        },
    }


def build_syrin_snippet(topology: str, budget: SwarmBudgetPlan) -> str:
    """Return an optional Syrin v0.11 snippet that users can adapt."""
    return f'''# Requires syrin>=0.11.0
import asyncio

from syrin import Agent, Budget, Model
from syrin.budget import BudgetPool
from syrin.enums import MemoryType, SwarmTopology
from syrin.swarm import A2AConfig, A2ARouter, MemoryBus, Swarm, SwarmConfig

pool = BudgetPool(total={budget.total_budget:.2f}, per_agent_max={budget.per_agent_max:.2f})
a2a = A2ARouter(config=A2AConfig(audit_all=True, max_queue_depth=100))
memory_bus = MemoryBus(
    allow_types=[MemoryType.KNOWLEDGE, MemoryType.INSTRUCTIONS],
    filter=lambda entry: not any(term in entry.content.lower() for term in {BLOCKED_MEMORY_TERMS!r}),
)

swarm = Swarm(
    agents=[OrchestratorAgent, MarketResearcherAgent, RouteEvaluatorAgent, AdvocacySellerOpsAgent],
    goal=task,
    budget=Budget(max_cost={budget.total_budget:.2f}),
    config=SwarmConfig(topology=SwarmTopology.{topology}),
)

# Route external paid work through Agoragentic only after approval evidence passes.
# Use SwarmController.topup_budget() or reallocate_budget() only with audit approval.
async def main() -> None:
    result = await swarm.run()
    print(result.content)


if __name__ == "__main__":
    asyncio.run(main())
'''


def build_swarm_router_plan(
    task: str,
    topology: str = "ORCHESTRATOR",
    total_budget: float = 1.0,
    per_agent_max: float = 0.25,
    live_enabled: bool = False,
    requested_action: str = "preview route",
    roles: tuple[str, ...] | None = None,
) -> SwarmRouterPlan:
    """Build a complete Syrin v0.11 plus Agoragentic swarm plan."""
    normalized_topology = topology.strip().upper() or "ORCHESTRATOR"
    budget = build_budget_plan(
        total_budget=total_budget,
        per_agent_max=per_agent_max,
        roles=roles,
    )
    return SwarmRouterPlan(
        task=task,
        topology=normalized_topology,
        budget=budget,
        a2a_contracts=build_a2a_contracts(roles),
        memory_bus_policy=memory_bus_policy(),
        audit_hooks=[
            "DECISION_MADE",
            "BUDGET_THRESHOLD",
            "TOOL_CALL_END",
            "MEMORY_WRITE",
            "A2A_MESSAGE_SENT",
        ],
        approval_report=guard_swarm_action(requested_action, live_enabled=live_enabled),
        execute_payload=build_execute_payload(
            task=task,
            budget=budget,
            topology=normalized_topology,
            live_enabled=live_enabled,
        ),
        syrin_snippet=build_syrin_snippet(normalized_topology, budget),
    )


def non_negative_float(value: str) -> float:
    """Parse a finite non-negative CLI float."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(parsed):
        raise argparse.ArgumentTypeError("must be finite")
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def main() -> None:
    """Print a preview-first Syrin swarm router plan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        default=(
            "Deploy a bounded Syrin swarm that scores leads, routes paid capability calls "
            "through Agoragentic, records receipts, and proposes one safe growth action."
        ),
    )
    parser.add_argument("--topology", default="ORCHESTRATOR")
    parser.add_argument("--total-budget", type=non_negative_float, default=1.0)
    parser.add_argument("--per-agent-max", type=non_negative_float, default=0.25)
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--requested-action", default="preview route")
    args = parser.parse_args()

    plan = build_swarm_router_plan(
        task=args.task,
        topology=args.topology,
        total_budget=args.total_budget,
        per_agent_max=args.per_agent_max,
        live_enabled=args.run_live,
        requested_action=args.requested_action,
    )
    print(json.dumps(plan.as_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
