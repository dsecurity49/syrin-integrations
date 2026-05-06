# Agoragentic starter kits

Starter kits package the Agoragentic x Syrin integration into deployment-shaped
folders instead of one-file examples.

Use a starter kit when you want:

- a served Syrin agent process
- a platform-hosted deployment scaffold with reviewed execution
- explicit environment variables and fail-closed defaults
- Docker, smoke-test assets, or hosted provider previews
- a clearer path from local development to self-hosted or platform-hosted deployment
- a clean split between Syrin control-plane responsibilities and Agoragentic execution-plane responsibilities

## Available starter kits

### `hosted_syrin_agent/`

A preview-first, self-hostable Syrin agent that exposes the standard Syrin HTTP
routes and uses Agoragentic as the capability router.

Includes:

- runtime config helpers with preview-first defaults
- served agent entrypoint
- Agent Lightning-compatible trace and reward export helpers
- Agent OS implementation prompt
- `.env.example`
- Dockerfile and `docker-compose.yml`
- `/health`, `/ready`, and `/describe` smoke test
- self-hosted now / platform-hosted later deployment notes

Start with [hosted_syrin_agent/README.md](hosted_syrin_agent/README.md).

### `platform_hosted_syrin_agent/`

A preview-first control-plane starter kit for platform-hosted Syrin deployment
plans.

Includes:

- runtime config helpers for reviewed hosted actions
- deterministic activation-gate and smoke-result helpers
- provider previews for App Runner, GPU bridge, and simulated lanes
- redacted vault handoff contracts
- a `launch_request.py` CLI for shaping deployment previews
- Agent OS implementation prompt
- explicit control-plane alignment with Syrin Nexus, Syrin CLI, and Syrin Python

Start with [platform_hosted_syrin_agent/README.md](platform_hosted_syrin_agent/README.md).
