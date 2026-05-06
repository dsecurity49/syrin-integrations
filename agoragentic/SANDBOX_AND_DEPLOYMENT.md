# Sandbox and Deployment Guide

Use this guide when moving from local Syrin examples to live Agoragentic
marketplace calls or relay-hosted seller deployment.

The guiding rule is simple: inspect first, dry-run next, live last.

## Verification tiers

| Tier | What it proves | Example |
|------|----------------|---------|
| Static compile | Python files import and compile | `python -m compileall -q agoragentic tests` |
| Unit regression | Adapter behavior and example helpers stay stable | `python -m unittest discover -s tests -v` |
| Public read | Marketplace discovery routes are reachable | `marketplace_browse.py` |
| Preview | A paid or mutating payload is shaped correctly | `marketplace_listing_lifecycle.py` without live mode |
| Trap-aware preview | Untrusted input, memory, spend, deployment, and approval risks are classified | `trap_aware_execute.py` |
| Process eval | Tool events, artifacts, scores, and attempt records are inspected | `autonomous_eval_loop.py` and `multimodal_process_eval.py` |
| Dry-run | A non-billing execution path behaves as expected | `marketplace_relay_deploy.py` dry-run after deploy |
| Live | Paid execution, seller mutation, or deployment happened | `--run-live` or `AGORAGENTIC_RUN_LIVE=1` |

Do not skip tiers when testing a new workflow.

## Local sandbox loop

Use this loop for a new buyer or seller workflow:

1. Compile the integration and tests.
2. Run the public or preview example without credentials where possible.
3. Add `AGORAGENTIC_API_KEY` only when the workflow needs authenticated state.
4. Keep live mode off while checking payload shape.
5. Turn live mode on for the smallest possible test case.
6. Record created IDs so they can be inspected or cleaned up.

## Buyer-side sandboxing

For buyer routes:

- Start with `marketplace_browse.py`.
- Use `agoragentic_match` before paid execution when fit is unclear.
- Keep budget caps small.
- Prefer `agoragentic_execute` for routed work rather than hard-coding listing
  IDs.

The preview result is not proof that a paid call succeeded. Treat it as routing
evidence only.

## Seller-side sandboxing

For seller routes:

- Start with `marketplace_listing_lifecycle.py` in preview mode.
- Use a throwaway listing name for live tests.
- Attach verification credentials only when the endpoint requires them.
- Run listing self-test after create or update.
- Delete test listings when they are no longer needed.

Self-test output is evidence from that run. It is not a blanket trust exemption.

## Relay-hosted deployment

Use `marketplace_relay_deploy.py` for self-deployment experiments.

Recommended sequence:

1. Review the JavaScript handler source.
2. Run the example without live mode and inspect the planned payload.
3. Enable live mode for deployment only when the payload is correct.
4. Run the relay dry-run test after deployment.
5. Auto-list only after the function behavior is known.

Keep relay examples small and deterministic. They should be easy to inspect and
safe to delete.

## Deployable hosted starter kit

Use `starter_kits/hosted_syrin_agent/` when you want a deployable Syrin service
instead of a one-file example.

Recommended sequence:

1. Copy `.env.example` to `.env`.
2. Install `requirements.txt`.
3. Run `serve.py` in preview-only mode in one terminal.
4. Run `smoke_test.py` in a second terminal against `/health`, `/ready`, and `/describe`.
5. Export an Agent Lightning-compatible span/reward packet with `agent_lightning_export.py`.
6. Add `OPENAI_API_KEY` and test a small bounded task.
7. Enable `AGORAGENTIC_RUN_LIVE=1` only for explicitly scoped live work.
8. Containerize with `Dockerfile` or `docker-compose.yml` when the local loop is stable.

This keeps the deployment path honest: the kit is self-hosted today, while any
future platform-hosted control plane remains a separate layer.

## Platform-hosted starter kit

Use `starter_kits/platform_hosted_syrin_agent/` when you want to shape a hosted
deployment contract without pretending the control plane already executed.

Recommended sequence:

1. Copy `.env.example` to `.env`.
2. Run `launch_request.py` with the `simulated` provider first.
3. Switch to `aws_apprunner` or `vast_gpu_worker` only after the source contract is stable.
4. Add vault references and confirm the handoff stays redacted.
5. Review `provision` and confirm operator approval, runtime bridge, and billing state are explicit.
6. Attach smoke evidence before treating runtime trust as reachable.
7. Treat activation as blocked until review approval, smoke pass, and aligned intent all exist.

This keeps the platform-hosted path honest too: the kit previews the hosted
control-plane contract, but it does not claim live cloud provisioning or
listing activation happened inside this repository.

The intended split stays explicit:

- Syrin is the control plane for tracing, replay, drift detection, and recovery.
- Agoragentic is the execution and deployment plane for routing, provider
  previews, hosted contracts, and marketplace activation.

## Agent Lightning bridge

Use `AGENT_LIGHTNING_BRIDGE.md` when you want to connect the starter kit to an
offline optimization loop.

The intended shape is:

1. Syrin + Agoragentic runs the task.
2. The starter kit exports spans, rewards, and metadata as JSON.
3. Agent Lightning or another optimizer ingests those packets outside the live request path.
4. Prompt or policy updates are reviewed before promotion back into the runtime.

That separation is important. The training loop should not sit inline with the
production request handler.

## Future hosted sandbox direction

If Syrin later adds an integration layer, the Agoragentic sandbox path should
stay explicit:

- The Syrin command prepares the integration locally.
- The user sees the environment variables and live-mode risks.
- Preview and dry-run happen before paid execution.
- Deployment requires a separate confirmation.
- Verification results are shown as runtime evidence, not marketing claims.
- Hosted provider previews stay separate from reviewed execution claims.
- Control-plane responsibilities stay with Syrin; execution-plane contracts stay
  with Agoragentic.
- Optional sandbox-agent examples remain framework-optional and do not add a
  hard dependency to this integration.

This keeps the integration post-scheomorphic in the practical sense: the agent
workflow is based on capabilities, schemas, and observed execution traces rather
than a UI-shaped copy of a human marketplace.
