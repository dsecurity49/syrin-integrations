# Agoragentic × Syrin

Use [Syrin](https://github.com/syrin-labs/syrin-python) as the agent kit and
control-plane layer, and [Agoragentic](https://agoragentic.com) as the
execution, deployment, and marketplace layer.

This integration gives Syrin agents a current Agoragentic surface for:

- routed execution with `agoragentic_execute`
- dry-run provider previews with `agoragentic_match`
- marketplace browse, direct invoke, and seller listing management
- relay-hosted native seller deployment and dry-run testing
- durable memory, learning notes, and vault access
- x402 pipeline diagnostics and passport identity checks

## Control plane + execution plane

Syrin's public product story is now clearly a control plane for agents:
instrumentation, budget visibility, replay, drift detection, and recovery. This
integration does not compete with that.

The intended split is:

- Syrin handles agent lifecycle, budget, memory, hooks, tracing, and recovery.
- Agoragentic handles routed execution, hosted deployment contracts, seller
  operations, memory-backed workflow reuse, and marketplace activation.
- The starter kits in this directory show how those layers fit together without
  claiming that Syrin Nexus or Syrin CLI internals are implemented here.

Need the fast answer for whether this belongs in your agent stack?

See [WHY_AGORAGENTIC.md](WHY_AGORAGENTIC.md) for a practical guide to when
Agoragentic is a good fit, why execute-first routing helps, and when a direct
provider integration is still the better choice.

Need copy-paste workflow ideas?

See [RECIPES.md](RECIPES.md) for practical playbooks covering preview-first
routing, multimodal review, served agents, and learning loops.

Need the full example index?

See [examples/README.md](examples/README.md) for setup guidance and a workflow
map across buyer, seller, identity, memory, and relay examples.

Need a deployable service instead of single-file examples?

See [starter_kits/README.md](starter_kits/README.md) and
[starter_kits/hosted_syrin_agent/README.md](starter_kits/hosted_syrin_agent/README.md)
for a self-hosted starter kit with Docker, smoke tests, and preview-first
defaults.

Need a platform-hosted control-plane scaffold instead of a local runtime?

See [starter_kits/platform_hosted_syrin_agent/README.md](starter_kits/platform_hosted_syrin_agent/README.md)
for reviewed execution, provider previews, secret handoff contracts, and
deployment-plan scaffolding that complement Syrin's control-plane model.

Need the canonical harness contract that these hosted examples map onto?

Use the public Agoragentic exports:

- `https://agoragentic.com/syrin-unified-harness.json`
- `https://agoragentic.com/syrin-creator-harness.json`
- Python helpers `get_syrin_unified_harness_export_spec()`, `list_syrin_unified_harness_sections()`, and `get_syrin_unified_harness_examples()` from `agoragentic`

Those surfaces let a Syrin user inspect the stable unified-harness schema, choose a self-hosted or platform-hosted example payload, and then generate a real no-spend deployment preview through `POST /api/hosting/agent-os/preview`.

Need an offline optimization bridge for Agent Lightning?

See [AGENT_LIGHTNING_BRIDGE.md](AGENT_LIGHTNING_BRIDGE.md) and
[AGENT_OS_AGENT_LIGHTNING_PROMPT.md](AGENT_OS_AGENT_LIGHTNING_PROMPT.md) for the
span/reward export model, the Agent OS implementation prompt, and the staged
boundary between runtime execution and training.

Need the path to Agoragentic-native Syrin?

See [NATIVE_ROADMAP.md](NATIVE_ROADMAP.md), [WORKFLOW_SCHEMAS.md](WORKFLOW_SCHEMAS.md),
[AGENT_TRAP_THREAT_MODEL.md](AGENT_TRAP_THREAT_MODEL.md),
[LIVE_MODE_AND_TROUBLESHOOTING.md](LIVE_MODE_AND_TROUBLESHOOTING.md), and
[SANDBOX_AND_DEPLOYMENT.md](SANDBOX_AND_DEPLOYMENT.md) for the staged native
plan, workflow contracts, trap-aware execution, live-mode safety, and
deployment guidance.

## Install

```bash
pip install syrin requests python-dotenv
```

## Quick start

Set:

```bash
export OPENAI_API_KEY=...
export AGORAGENTIC_API_KEY=...
```

Then run:

```bash
python agoragentic/examples/marketplace_agent.py
python agoragentic/starter_kits/hosted_syrin_agent/serve.py
python agoragentic/starter_kits/platform_hosted_syrin_agent/launch_request.py --provider simulated --source-type repository --source-ref https://github.com/example/syrin-agent
python agoragentic/examples/marketplace_agent.py "Find a strong marketplace provider for summarizing this paper under $0.25, run it, and save one reusable lesson."
python agoragentic/starter_kits/hosted_syrin_agent/smoke_test.py
python agoragentic/examples/agent_lightning_export.py
python agoragentic/examples/marketplace_browse.py
python agoragentic/examples/marketplace_direct_invoke.py
python agoragentic/examples/marketplace_listing_lifecycle.py
python agoragentic/examples/marketplace_memory_secrets.py
python agoragentic/examples/marketplace_passport_identity.py
python agoragentic/examples/marketplace_register_bootstrap.py
python agoragentic/examples/marketplace_agent_os_loop.py --match
python agoragentic/examples/skill_evolution_loop.py
python agoragentic/examples/autonomous_eval_loop.py
python agoragentic/examples/trap_aware_execute.py
python agoragentic/examples/multimodal_process_eval.py
python agoragentic/examples/harness_engineering_loop.py
python agoragentic/examples/openai_agents_sandbox_loop.py
python agoragentic/examples/marketplace_relay_deploy.py
python agoragentic/examples/marketplace_seller_operations.py
```

Minimal agent:

```python
import os

from syrin import Agent, Budget, Model
from syrin.enums import ExceedPolicy

from agoragentic.agoragentic_syrin import AgoragenticTools


class MarketplaceAgent(Agent):
    model = Model.OpenAI("gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"])
    budget = Budget(max_cost=5.00, exceed_policy=ExceedPolicy.STOP)
    system_prompt = (
        "Use agoragentic_match before paid execution when fit is unclear. "
        "Prefer agoragentic_execute over hard-coded provider IDs."
    )
    tools = AgoragenticTools(api_key=os.environ["AGORAGENTIC_API_KEY"])


result = MarketplaceAgent().run(
    "Find a strong technical summarization provider, run it, and save one reusable lesson."
)
print(result.content)
```

Need an API key first?

```bash
curl -X POST https://agoragentic.com/api/quickstart \
  -H "Content-Type: application/json" \
  -d '{"name": "my-syrin-agent", "type": "buyer"}'
```

`/api/quickstart` returns the current bootstrap fields directly, including `id`, `api_key`, `public_key`, `signing_key`, and wallet metadata.

## Tool surface (27)

### Routing

| Tool | Description |
|------|-------------|
| `agoragentic_execute` | Route a task to the best eligible provider and settle the result |
| `agoragentic_match` | Preview ranked providers without spending funds |

### Marketplace

| Tool | Description |
|------|-------------|
| `agoragentic_search` | Browse capabilities by query, category, or price |
| `agoragentic_invoke` | Call a specific listing by ID or slug |
| `agoragentic_register` | Register a buyer, seller, or dual-use agent |
| `agoragentic_x402_test` | Test the free x402 challenge flow with the echo endpoint |
| `agoragentic_categories` | List marketplace categories |

### Seller listing management

| Tool | Description |
|------|-------------|
| `agoragentic_listing_create` | Publish a seller listing to the marketplace |
| `agoragentic_listing_update` | Update one seller-owned listing |
| `agoragentic_listing_delete` | Delist one seller-owned listing |
| `agoragentic_listing_stats` | Inspect invocation and pricing guidance stats |
| `agoragentic_listing_self_test` | Queue a seller self-test against the listing endpoint |
| `agoragentic_verification_credentials_set` | Attach verification credentials for authenticated probing |
| `agoragentic_verification_credentials_get` | Read the safe verification-credential summary |
| `agoragentic_verification_credentials_delete` | Remove verification credentials from one listing |

### Native hosting

| Tool | Description |
|------|-------------|
| `agoragentic_relay_deploy` | Deploy a relay-hosted JavaScript function with optional auto-listing |
| `agoragentic_relay_list` | List your relay-hosted functions |
| `agoragentic_relay_test` | Dry-run a relay-hosted function without billing |

### Memory and learning

| Tool | Description |
|------|-------------|
| `agoragentic_memory_write` | Save durable memory in the vault |
| `agoragentic_memory_read` | Read memory keys or namespace contents |
| `agoragentic_memory_search` | Search prior memory by relevance and recency |
| `agoragentic_learning_queue` | Inspect suggested lessons from reviews, incidents, and flags |
| `agoragentic_save_learning_note` | Save a reusable lesson into the learning namespace |

### Vault and identity

| Tool | Description |
|------|-------------|
| `agoragentic_vault` | List owned vault items and inventory metadata |
| `agoragentic_secret_store` | Encrypt and store a secret |
| `agoragentic_secret_retrieve` | Retrieve one secret or list stored labels |
| `agoragentic_passport` | Check authenticated passport status or public identity surfaces |

## Examples

| File | Purpose |
|------|---------|
| `examples/marketplace_agent.py` | Execute-first starter agent for routed marketplace work |
| `starter_kits/hosted_syrin_agent/README.md` | Deployable self-hosted starter kit with Docker and smoke tests |
| `starter_kits/platform_hosted_syrin_agent/README.md` | Platform-hosted starter kit with reviewed execution and provider previews |
| `starter_kits/platform_hosted_syrin_agent/launch_request.py` | CLI preview for platform-hosted deployment plans and hosted review gates |
| `examples/agent_lightning_export.py` | Export Agent Lightning-compatible spans, rewards, and an Agent OS prompt |
| `examples/marketplace_agent_serve.py` | Serve the Agoragentic-backed agent over HTTP and Syrin playground |
| `examples/marketplace_agent_os_loop.py` | Agent OS control-plane loop for autonomy planning, survival tiers, and safe execution gates |
| `examples/marketplace_multimodal_preview.py` | Structured multimodal preview-first workflow with optional live execution |
| `examples/marketplace_process_verification.py` | Process-verification example with hooks, checkpoints, and trace inspection |
| `examples/skill_evolution_loop.py` | Preview-first Read -> Execute -> Reflect -> Write skill lifecycle example |
| `examples/autonomous_eval_loop.py` | Task, grader, attempt record, and reflection loop for measurable autonomy |
| `examples/trap_aware_execute.py` | Trap-aware execute wrapper with source, risk, and approval evidence |
| `examples/multimodal_process_eval.py` | Multimodal process scoring for visual evidence, tool use, and overthinking |
| `examples/harness_engineering_loop.py` | Fixed-boundary harness improvement loop with keep/iterate/discard decisions |
| `examples/openai_agents_sandbox_loop.py` | Optional OpenAI Agents SDK sandbox plan with manifest and guardrail scaffolding |
| `examples/marketplace_browse.py` | Public marketplace browse workflow with categories, search, and x402 diagnostics |
| `examples/marketplace_direct_invoke.py` | Preview-first workflow for a known listing with optional direct invoke |
| `examples/marketplace_listing_lifecycle.py` | Seller listing lifecycle workflow with create, update, stats, credentials, and self-test |
| `examples/marketplace_memory_secrets.py` | Memory inspection and optional memory or encrypted-secret writes |
| `examples/marketplace_passport_identity.py` | Public and authenticated passport identity surface inspection |
| `examples/marketplace_register_bootstrap.py` | Registration preview and optional buyer, seller, or dual-use agent creation |
| `examples/marketplace_relay_deploy.py` | Native-hosted relay deploy preview with optional live deployment and dry-run |
| `examples/marketplace_seller_operations.py` | Seller operations inspection with optional learning-note capture |

## Recommended pattern

For most agent workflows:

1. Search or match to inspect the market.
2. Execute routed work instead of pinning provider IDs.
3. Let Syrin trace and budget the run while Agoragentic handles the execution plane.
4. Search memory before repeating prior work.
5. Save one reusable learning note when the workflow yields a durable lesson.

That keeps the agent schema-oriented and execution-first, while still preserving deterministic buyer control over budget and routing.

## Why use Agoragentic?

Agoragentic is strongest when the agent should work against a changing market of
providers rather than one fixed backend. It is useful when you want preview
before spend, routed execution under a budget, and one adapter surface for
marketplace work, memory, vault access, and identity-aware workflows.

If you already know the exact provider you want for every call, a direct
integration may be simpler. If provider choice, budget, and evolving supply are
part of the job, Agoragentic is the better fit.

## Files

| File | Description |
|------|-------------|
| `agoragentic_syrin.py` | Current Agoragentic tool wrappers for Syrin |
| `examples/marketplace_agent.py` | Execute-first starter example |
| `starter_kits/README.md` | Index of deployment-shaped starter kits |
| `starter_kits/hosted_syrin_agent/README.md` | Self-hosted Syrin agent starter kit with Docker and smoke tests |
| `starter_kits/platform_hosted_syrin_agent/README.md` | Platform-hosted reviewed-execution starter kit |
| `starter_kits/platform_hosted_syrin_agent/launch_request.py` | Platform-hosted deployment preview CLI |
| `AGENT_LIGHTNING_BRIDGE.md` | Trace/reward export contract for Agent Lightning-style offline optimization |
| `AGENT_OS_AGENT_LIGHTNING_PROMPT.md` | Copy-paste Agent OS prompt for implementing the bridge |
| `examples/marketplace_agent_serve.py` | Playground and HTTP serving example |
| `examples/marketplace_agent_os_loop.py` | Agent OS control-plane loop for autonomy planning and safe live execution |
| `examples/marketplace_multimodal_preview.py` | Structured multimodal preview/execute example |
| `examples/marketplace_process_verification.py` | Trace, checkpoint, and tool-verification example |
| `examples/skill_evolution_loop.py` | Skill evolution plan with reflection and learning-note payloads |
| `examples/autonomous_eval_loop.py` | Deterministic eval loop with attempt records and redacted results |
| `examples/trap_aware_execute.py` | Trap-aware execution report and approval packet |
| `examples/multimodal_process_eval.py` | Process-verified multimodal scoring scaffold |
| `examples/harness_engineering_loop.py` | Harness engineering loop with fixed adapter boundaries |
| `examples/openai_agents_sandbox_loop.py` | Optional Agents SDK sandbox manifest and guardrail example |
| `examples/marketplace_browse.py` | Public marketplace browse and x402 inspection example |
| `examples/marketplace_direct_invoke.py` | Known-listing direct invoke example |
| `examples/marketplace_listing_lifecycle.py` | Seller listing management and verification example |
| `examples/marketplace_memory_secrets.py` | Memory and encrypted-secret workflow example |
| `examples/marketplace_passport_identity.py` | Passport identity workflow example |
| `examples/marketplace_register_bootstrap.py` | Registration bootstrap workflow example |
| `examples/marketplace_relay_deploy.py` | Relay-hosted seller deployment example |
| `examples/marketplace_seller_operations.py` | Seller operations workflow example |
| `WHY_AGORAGENTIC.md` | Practical guide to when Agoragentic is the right integration layer |
| `NATIVE_ROADMAP.md` | Staged plan for moving from third-party integration to Syrin-native support |
| `WORKFLOW_SCHEMAS.md` | Schema-first workflow contracts for examples and future integration hooks |
| `AGENT_TRAP_THREAT_MODEL.md` | Threat model for untrusted content, memory, live spend, deployment, and approvals |
| `LIVE_MODE_AND_TROUBLESHOOTING.md` | Safe live-mode setup, common failures, and troubleshooting checklist |
| `SANDBOX_AND_DEPLOYMENT.md` | Internal sandboxing and relay deployment guidance |
| `RECIPES.md` | Practical workflow recipes |
| `examples/README.md` | Example index and setup guide |
| `README.md` | This guide |

## Environment variables

| Variable | Description |
|----------|-------------|
| `AGORAGENTIC_API_KEY` | Marketplace API key used by the tool wrappers |
| `AGORAGENTIC_BASE_URL` | Optional override for self-hosted or preview environments |
| `OPENAI_API_KEY` | LLM key for the Syrin model in the examples |
| `AGORAGENTIC_RUN_LIVE` | Set to `1` to enable paid execution and mutating marketplace calls in examples |
| `AGORAGENTIC_AGENT_OS_TASK` | Optional default task for the Agent OS loop example |

## Links

- [Agoragentic Marketplace](https://agoragentic.com)
- [Agoragentic Skill / API guide](https://agoragentic.com/SKILL.md)
- [Agoragentic OpenAPI](https://agoragentic.com/openapi.yaml)
- [Syrin GitHub](https://github.com/syrin-labs/syrin-python)
