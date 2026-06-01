# TECHNICAL.md

## API Reference

### `IntentBusSyrinHarness`
The core execution engine bridging synchronous SDK listeners with asynchronous Syrin agents.

**`__init__(agent_factory, bus, capabilities=None, telemetry_filter=None, observer=None, mission_timeout=900, node_name="worker")`**
* `agent_factory` (Callable): Function returning a freshly instantiated `syrin.Agent`.
* `bus` (IntentClient): The initialized Intent Bus client.
* `capabilities` (List[str]): List of string tags (e.g., `['gpu', 'bash']`) used for intent routing.
* `telemetry_filter` (Set[str]): Defines which events (`thought`, `tool_call`, `run_end`, `error`) are pushed to the observer.
* `observer` (ChiasmObserver | None): Optional telemetry sink for UI dashboards.
* `mission_timeout` (int): Hard timeout limit in seconds. Reaping occurs if execution exceeds this.
* `node_name` (str): Aesthetic identifier for logging and tracing.

**`serve(goal: str, namespace: str = "default")`**
* **Behavior:** Blocking call that starts the internal `WorkerRuntime.listen` loop. Spawns a background `threading.Thread` to run the async event loop without blocking the main Python thread.
* **Interrupts:** Safely catches `KeyboardInterrupt` to invoke the `.shutdown()` sequence, cancelling pending tasks and closing network sockets.

### `SyrinMissionContext`
Manages the isolated state and lifecycle of a single executed mission.

* **`persist_state(state_blob: Any)`**: Asynchronously serializes and writes the agent's checkpoint to the Intent Bus KV store (TTL 24h).
* **`recover_state() -> Optional[Any]`**: Fetches the previous checkpoint from the KV store. Returns `None` if `not_found`.
* **`emit_telemetry(event_type: str, payload: dict)`**: Publishes internal agent events back to the Intent Bus as new intents (goal: `syrin_trace_{event_type}`).
* **`heartbeat(interval: int = 15, extension: int = 120)`**: Infinite loop maintaining the worker's lock on the mission. Tolerates up to 3 consecutive network failures before terminating.

### `ChiasmObserver`
**`__init__(chiasm_url, api_key, node_name)` / `.notify(mission_id, event_type, data)`**
* Expects `run_end` or `error` events to trigger `PATCH /tasks/{id}`.
* Drops telemetry silently on 2-second timeout to prevent stalling the worker loop.

---

## Protocol Details

### Intent Envelope
* **Required:** `id` (32-char hex), `payload` (JSON dict).
* **Syrin Standard:** The `payload` MUST contain an `"instruction"` key (string). Missing this raises a `ValueError` before agent execution.

### Mission Lifecycle
1. **Open:** Intent resides on the server queue.
2. **Claimed:** Worker atomically locks the intent. `heartbeat()` begins extending the lease.
3. **Fulfilled/Dead:** Worker posts the final result or error. Lease drops.

### State Persistence Schema
* **Key Format:** `syrin:m:{mission_id}:state`
* **TTL:** 86400 seconds (24 hours).
* **Format:** Must be standard JSON-serializable types.

---

## Performance & Tuning

* **Heartbeat Interval:** Defaults to 15s extending by 120s. Adjust lower for highly volatile networks.
* **Claim Timeout:** Intent Bus defaults to 60s. The worker extends this proactively. If the worker hard-crashes, the server waits 60s before requeuing.
* **Mission Timeout:** Defaults to 900s. Large coding tasks or deep research may require bumping this to 3600s.
* **Concurrency:** The harness uses a single event loop per Python process. For higher throughput, spawn multiple process replicas rather than utilizing async concurrency.
* **Latency:** Chiasm UI telemetry has a hard 2s HTTP timeout. Intent Bus RPC calls use standard retry backoffs.

---

## Debugging & Troubleshooting

### Telemetry & Logs
Enable `--verbosity DEBUG` to view the agent's internal `[🧠] thought` stream and raw tool executions.

### Common Failure Modes
1. **`[Authentication Failure]`**: Intent Bus or LLM API key is invalid/expired. *Fix: Check hidden dotfiles.*
2. **`[Execution Timeout]`**: Agent got stuck in a reasoning loop. *Fix: Increase `--timeout` or simplify the prompt.*
3. **State Corruption**: The KV blob was modified manually or schema changed. *Fix: Manually delete the key via `client.delete("syrin:m:{id}:state")`.*

### Server Tools
* Read dead-letter intents using the Intent Bus `/admin/dead` API to inspect payloads that repeatedly crash workers.
* Check KV state via standard python REPL: `client.get("syrin:m:{id}:state")`.

---

## Architecture Deep Dive

* **The Threading Model:** The Intent Bus SDK uses synchronous HTTP blocking calls. Syrin relies heavily on `asyncio`. The harness boots the `asyncio.new_event_loop()` inside a daemon thread, using `run_coroutine_threadsafe` to bridge the two worlds perfectly.
* **Error Translation:** `_translate_error()` intercepts raw API tracebacks (e.g., `litellm.exceptions.RateLimitError`) and converts them into standardized, color-coded terminal messages, preventing messy stack traces in the logs.
* **The Universal Adapter Pattern:** Syrin natively relies on explicit provider builders (`Model.Google`, `Model.Anthropic`). To achieve true provider-agnosticism without modifying the core framework, `worker.py` implements a Universal Adapter. By capturing the `--api-base` argument from the configuration profile, the worker dynamically overrides `os.environ["OPENAI_BASE_URL"]` and forces Syrin's `Model.OpenAI` class to treat *any* OpenAI-compatible endpoint (like Groq, OpenRouter, or Ollama) as if it were a native OpenAI connection.

---

## Multi-Worker Patterns

* **Capability Routing:** Start specific workers with `--caps gpu,python`. Publishers can require these exact tags, guaranteeing heavy workloads only hit capable machines.
* **Namespace Isolation:** Deploy a set of workers to `--namespace engineering` and another to `--namespace marketing` on the same Bus.
* **Load Balancing:** Priority is handled server-side. Multiple workers listening to the same `goal` and `namespace` automatically act as a round-robin load balancer.

---

## Known Gotchas

* **State Blobs:** Must be strictly JSON-serializable. No custom Python classes.
* **Telemetry Loss:** The ChiasmObserver is non-blocking. If the dashboard is down, logs are silently dropped to keep the worker alive.
* **ID Truncation:** Full IDs are 32 characters, but terminal logs truncate to `[:8]` (e.g., `[23d27b36]`) for readability.
