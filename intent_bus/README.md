# Intent Bus + Syrin Integration

Run Syrin agents as distributed workers. No open ports, atomic routing, built-in retries.

## Why Intent Bus?
* Workers poll outbound (no open ports required)
* Atomic claim semantics (at-least-once execution)
* Exponential backoff + dead-letter queue
* Lightweight SQLite backend
* State persistence between claims

## When to Use
**✅ Good Fit:** Background AI agents, web scrapers, long-running research tasks, asynchronous code review bots.
**❌ Bad Fit:** Microsecond-latency microservices, real-time gaming backends, billions of events per second.

## Architecture & Ecosystem Comparison

| Tool | Core Philosophy | Best For |
| :--- | :--- | :--- |
| **Intent Bus** | Lightweight, poll-based, zero-trust network friendly. | Decentralized AI agents, unreliable networks. |
| **Celery** | Heavyweight, broker-dependent (Redis/RabbitMQ). | Standard Django/Python monolith background tasks. |
| **Temporal** | Highly complex, durable execution state machine. | Enterprise financial transactions, massive orchestration. |

```text
[Publisher Script] 
       |
       | (Publish: {instruction: "Analyze..."})
       v
+-----------------------+
|  Intent Bus Server    | <--- (KV Store for State)
+-----------------------+
       ^
       | (Atomic Long-Poll Claim)
       |
[Syrin Worker Node 1] ---> Spawns Thread ---> Executes Syrin Agent
                                                  |
                                                  +---> (Outputs Result)
```

## Quick Start
```bash
pip install intent-bus syrin pyyaml
echo "your-bus-key" > ~/.apikey
echo "your-gemini-key" > ~/.geminikey

# Terminal 1: Start the worker
python worker.py

# Terminal 2: Dispatch a mission
python trigger.py "Analyze this code"
```

## Real Output Example
```text
--- SYRIN SUBSTRATE RUNTIME v7.0 ---
 Node:         worker-1
 Listening:    default / gemma_test_mission
 Capabilities: ['gemma', 'termux-isolated']
 Verbosity:    INFO

[23d27b36] [worker-1] ⚡ MISSION RECEIVED: Perform a system check. Reply with exactly this...
[23d27b36] [worker-1] 🟢 MISSION COMPLETE.
STATUS_GREEN_MISSION_1
```

## Files
* `intent_bus_syrin.py` — Harness (routing, heartbeat, error translation)
* `worker.py` — Full Gemma 4 agent worker with argparse
* `trigger.py` — CLI to publish missions
* `interface.py` — Interactive REPL (optional)

## Documentation
* [Installation & Setup](INSTALL.md)
* [Advanced Examples & Architecture](examples/README.md)
* [Technical API Reference](TECHNICAL.md)
