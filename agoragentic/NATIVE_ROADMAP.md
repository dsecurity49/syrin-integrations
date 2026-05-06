# Agoragentic-Native Syrin Roadmap

This document defines what "Agoragentic-native" should mean for Syrin without
requiring Syrin core changes before the integration has usage proof.

The current state is official third-party integration: Syrin users can import
the adapter, run examples, and use Agoragentic as an execute-first capability
router. The target state is a first-class Syrin workflow where users can enable
Agoragentic, route capability work, test safely, and deploy seller functions
without copying integration code by hand.

The design assumption is that Syrin remains the control plane and agent
lifecycle layer, while Agoragentic supplies the execution plane, deployment
contracts, and marketplace surfaces.

## Native levels

| Level | Meaning | Current status |
|-------|---------|----------------|
| Compatible | Syrin can call Agoragentic through adapter tools | Done |
| Third-party native | Examples, docs, tests, and safe defaults live in `syrin-integrations/agoragentic` | In progress |
| Workflow native | Buyer, seller, memory, identity, multimodal, sandbox, and relay flows are documented and runnable | In progress |
| Schema native | Workflow payloads have stable contracts and validation guidance | In progress |
| Lifecycle native | Agents can run measurable skill, eval, trap-aware, multimodal, and harness loops in preview mode | In progress |
| Core native | Syrin has a first-class integration path such as `syrin integrate agoragentic` | Future maintainer decision |

## Phase 1: Official third-party native

Goal: make the integration useful from this repository without changing Syrin
core.

Acceptance criteria:

- `agoragentic/README.md` explains the adapter, install steps, and tool surface.
- `agoragentic/examples/README.md` maps examples by user workflow.
- `WHY_AGORAGENTIC.md` explains when Agoragentic is the right fit.
- `LIVE_MODE_AND_TROUBLESHOOTING.md` makes dry-run and live-mode risk explicit.
- CI compiles the adapter and runs the local regression tests.

Maintainer ask:

- Merge docs and examples here first.
- Avoid core CLI work until usage patterns are clearer.

## Phase 2: Workflow native

Goal: make each common Agoragentic workflow runnable by a Syrin user.

Covered workflows:

- Buyer routing with `marketplace_agent.py`
- Public browse and x402 diagnostics with `marketplace_browse.py`
- Known-listing invocation with `marketplace_direct_invoke.py`
- Agent OS autonomy planning with `marketplace_agent_os_loop.py`
- Multimodal preview-first routing with `marketplace_multimodal_preview.py`
- Memory, learning, and encrypted-secret operations with `marketplace_memory_secrets.py`
- Passport and identity inspection with `marketplace_passport_identity.py`
- Registration bootstrap with `marketplace_register_bootstrap.py`
- Seller listing lifecycle management with `marketplace_listing_lifecycle.py`
- Seller operations inspection with `marketplace_seller_operations.py`
- Relay-hosted seller deployment with `marketplace_relay_deploy.py`
- Process verification with `marketplace_process_verification.py`
- Skill evolution with `skill_evolution_loop.py`
- Autonomous task grading and attempt records with `autonomous_eval_loop.py`
- Trap-aware execution with `trap_aware_execute.py`
- Multimodal process evaluation with `multimodal_process_eval.py`
- Harness engineering with `harness_engineering_loop.py`
- Optional sandbox-agent planning with `openai_agents_sandbox_loop.py`

Acceptance criteria:

- Each workflow is documented as dry-run first unless it is read-only.
- Mutating or paid actions require `--run-live` or `AGORAGENTIC_RUN_LIVE=1`.
- User-facing docs distinguish marketplace preview, live execution, seller
  mutation, and relay deployment.
- Agent OS examples classify operating pressure without claiming production
  autonomy unless live execution and spend gates are explicitly enabled.

Maintainer ask:

- Treat these examples as the proving ground for future Syrin CLI integration.
- Point users here when they ask how to use Agoragentic from Syrin today.

## Phase 3: Schema native

Goal: make workflows predictable enough for agents to reason about and for CI to
catch drift.

Schema direction:

- Keep a small common envelope for workflow inputs.
- Separate preview, dry-run, live execution, and mutation modes.
- Prefer `agoragentic_execute` for routed buyer work.
- Use direct invoke only when the listing ID or slug is intentionally fixed.
- Document expected output fields and failure modes.

Acceptance criteria:

- `WORKFLOW_SCHEMAS.md` defines stable workflow contracts.
- Example payloads show which fields are required, optional, and live-only.
- New examples follow the same envelope instead of inventing custom argument
  shapes for each file.

Maintainer ask:

- Review the schema direction before we propose any Syrin core integration.
- Keep the contracts in the integration repo until they prove stable.

## Phase 4: Sandbox and deployment native

Goal: let users test internally before paying, mutating listings, or deploying a
seller capability.

Acceptance criteria:

- `SANDBOX_AND_DEPLOYMENT.md` documents safe local verification tiers.
- Relay deployment is preview-first and live-gated.
- Seller listing self-test is documented as a verification step, not a blanket
  trust claim.
- `starter_kits/platform_hosted_syrin_agent/` previews hosted provider
  contracts, reviewed execution gates, and secret handoff without claiming live
  cloud provisioning happened.
- The platform-hosted starter kit explicitly complements Syrin control-plane
  products such as Nexus or CLI instead of pretending to replace them.
- The docs do not imply runtime verification happened unless the user actually
  ran a live check.

Maintainer ask:

- Keep sandbox and deployment behavior explicit and conservative.
- Use the integration examples as a template for future Syrin-hosted sandboxes.

## Phase 5: Autonomous lifecycle native

Goal: make self-improving agent workflows concrete without enabling silent live
mutation.

Acceptance criteria:

- Skill evolution uses preview-first Read -> Execute -> Reflect -> Write plans.
- Eval loops record task, grader, score, attempt, and reflection metadata.
- Trap-aware execution classifies untrusted content before memory, spend,
  deployment, or approval actions.
- Multimodal workflows record visual/search process evidence and overthinking
  cost.
- Harness improvements respect a fixed adapter boundary and keep/discard based
  on measured score.
- Optional sandbox-agent examples remain framework-optional and do not add a
  hard dependency to this integration.

Maintainer ask:

- Treat these as proving-ground examples, not core Syrin behavior yet.
- Promote the patterns that users actually run safely.

## Phase 6: Core Syrin native

Goal: propose a Syrin-managed integration flow after the third-party integration
has enough real usage.

Future proposal shape:

```text
syrin integrate agoragentic
```

The command could install or copy the integration from `syrin-integrations`,
show required environment variables, create a starter agent, and link to the
workflow docs.

Do not implement this in Syrin core yet unless the maintainer explicitly wants
it. The current better path is to prove the workflows in this repository first.

Maintainer ask:

- Once users are using the integration, decide whether Syrin core should expose
  a formal integration layer.
- If yes, use this repository as the source package and these docs as the UX
  contract.

## Short definition

Syrin becomes Agoragentic-native when a user can keep Syrin as the control
plane, route work through `agoragentic_execute`, test the flow safely, and
deploy or manage seller capabilities without hand-copying examples.
