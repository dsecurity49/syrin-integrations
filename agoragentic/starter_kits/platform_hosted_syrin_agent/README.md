# Platform-Hosted Syrin Agent Starter Kit

This starter kit turns the Agoragentic x Syrin integration into a platform-hosted
control-plane scaffold. It does not start cloud infrastructure automatically.
Instead, it gives Syrin users a preview-first path for building hosted
deployment plans, reviewed execution claims, provider previews, and secret
handoff contracts.

This kit is intentionally aligned with Syrin's public control-plane direction:
Syrin remains the place for instrumentation, drift visibility, replay, and
runtime recovery, while Agoragentic provides the execution-plane contracts for
routing, hosting, activation, and marketplace-facing deployment.

Use it when you want:

- a platform-hosted deployment record rather than a local `serve.py` process
- explicit provider planning for App Runner, GPU bridge, or simulated lanes
- reviewed execution gates for provision, smoke, activation, and self-serve launch
- redacted vault handoff instead of inline secret values
- an honest bridge from self-hosted Syrin to a future hosted control plane

## What it ships

- `config.py` builds the hosted control-plane profile and startup notes.
- `deployment.py` shapes deployment plans, smoke results, and activation gates.
- `hosted_provider.py` normalizes provider aliases, vault handoff, and provider previews.
- `reviewed_executor.py` builds deterministic allow or deny decisions for hosted actions.
- `launch_request.py` prints a copy-paste deployment preview from the command line.
- `agent_os_prompt.py` gives another implementation agent a safe extension prompt.

## Quick start

From the repository root:

```bash
cp agoragentic/starter_kits/platform_hosted_syrin_agent/.env.example agoragentic/starter_kits/platform_hosted_syrin_agent/.env
python agoragentic/starter_kits/platform_hosted_syrin_agent/launch_request.py
python agoragentic/starter_kits/platform_hosted_syrin_agent/launch_request.py \
  --provider aws_apprunner \
  --source-type repository \
  --source-ref https://github.com/example/syrin-agent \
  --review-action provision
```

The output is a JSON preview. It does not begin cloud provisioning, billing, or
listing activation.

## Environment

Copy `.env.example` and set the provider lane plus the hosted-review gates you
want to simulate:

- `PLATFORM_HOSTED_PROVIDER`
- `AGORAGENTIC_RUN_LIVE`
- `PLATFORM_HOSTED_RUNTIME_BRIDGE_WIRED`
- `PLATFORM_HOSTED_BILLING_AUTHORIZED`
- `PLATFORM_HOSTED_OPERATOR_APPROVED`
- `PLATFORM_HOSTED_SERVICE_URL`

Important defaults:

- `PLATFORM_HOSTED_PROVIDER=simulated`
- `AGORAGENTIC_RUN_LIVE=0`
- `PLATFORM_HOSTED_RUNTIME_BRIDGE_WIRED=0`
- `PLATFORM_HOSTED_BILLING_AUTHORIZED=0`
- `PLATFORM_HOSTED_OPERATOR_APPROVED=0`

## Reviewed execution

The kit uses deterministic reviewed-action semantics:

- `provision` requires operator approval, runtime bridge wiring, live effects, and billing authorization
- `smoke` requires a service attachment
- `activate` requires a passed smoke result and aligned intent in addition to service attachment
- `self_serve_launch` stays blocked until the activation gate is open

That keeps platform-hosted flows honest. A shaped payload is not the same thing
as a real hosted deployment.

## Provider lanes

### `simulated`

Use this lane when you only want a no-op preview contract.

### `aws_apprunner`

Builds a preview for:

- repository-backed launches with branch, directory, runtime, build command, and start command
- container-image launches with image identifier, repository type, and port
- secret injection via AWS Secrets Manager or SSM ARN references only

### `vast_gpu_worker`

Builds a preview for:

- GPU bridge runtime lanes
- repository or image sources
- runtime environment variables and provider refs without direct cloud calls

## Secret handoff

Inline secrets are rejected. The starter kit only accepts redacted references
with the `agoragentic.agent-os.vault-handoff.v1` schema and the boundary
`adapter_injection_only`.

That is deliberate. Platform-hosted previews should never leak credential
material into logs, plans, or review packets.

## Recommended operator loop

1. Start with the `simulated` provider and inspect the deployment plan.
2. Switch to `aws_apprunner` or `vast_gpu_worker` only after the source contract is stable.
3. Attach secret references and confirm the vault handoff stays redacted.
4. Review `provision` and confirm the gate state is explicit.
5. Add smoke evidence and aligned intent only after the runtime contract is known.
6. Treat activation as blocked until review, smoke, and intent all agree.

## Relationship to the self-hosted kit

`hosted_syrin_agent/` is the runtime baseline:

- you run the process
- you control keys directly
- you validate `/health`, `/ready`, and `/describe`

`platform_hosted_syrin_agent/` is the control-plane baseline:

- you shape hosted deployment contracts
- you review hosted actions explicitly
- you keep runtime trust tied to evidence, not assumptions

## Relationship to Syrin products

This repository does not attempt to implement Syrin Nexus or Syrin CLI
internals. The intent is to give Syrin users an Agoragentic-native execution
plane that can sit beside those Syrin surfaces:

- Syrin Python provides the local agent framework
- Syrin CLI can remain the operator entrypoint
- Syrin Nexus can remain the hosted observation and recovery layer
- Agoragentic adds routed execution, deployment contracts, provider previews,
  and marketplace activation workflows

Together they form the current self-hosted now / platform-hosted next path.

## Related files

- [../README.md](../README.md)
- [../hosted_syrin_agent/README.md](../hosted_syrin_agent/README.md)
- [../../SANDBOX_AND_DEPLOYMENT.md](../../SANDBOX_AND_DEPLOYMENT.md)
- [../../NATIVE_ROADMAP.md](../../NATIVE_ROADMAP.md)
