# Installation & Configuration

## Prerequisites
* Python 3.10+
* Intent Bus Server (local or remote)
* API Keys (Intent Bus, LLM Provider, optional Chiasm)

## Version Compatibility
* `intent-bus` >= 2.0.4 (Strictly required for strongly-typed data models)
* `syrin` >= 1.0.0
* `pyyaml` (Optional, required only if using `.yaml` profiles)

## Setup
1. Install dependencies:
   ```bash
   pip install intent-bus syrin pyyaml
   ```
2. Configure credentials in your home directory:
   ```bash
   echo "your-bus-key" > ~/.apikey
   echo "your-gemini-key" > ~/.geminikey
   echo "your-chiasm-key" > ~/.chiasmkey
   chmod 600 ~/.apikey ~/.geminikey ~/.chiasmkey
   ```

## Verification
Confirm the system is wired correctly before processing real jobs:
```bash
# 1. Start worker in ping mode
python worker.py --ping
# Output should show: ✅ Intent Bus API Key found. ✅ GEMINI API Key found.

# 2. Start worker normally
python worker.py --fast

# 3. Open a second terminal and trigger a test
python trigger.py "Reply with the word SUCCESS"
```

## Start Worker
**Basic Start:**
```bash
python worker.py
```
**With Custom Options:**
```bash
python worker.py --model groq/llama3-8b-8192 --node worker-2 --verbosity DEBUG
```

## Publish Missions
**Using Trigger CLI:**
```bash
python trigger.py "Summarize this log file"
python trigger.py "Review PR" --profile examples/profiles/reviewer.json
```
**Using Interactive REPL:**
```bash
python interface.py
```

## Worker CLI Arguments
| Argument | Description | Default |
| :--- | :--- | :--- |
| `--goal` | Target intent goal to listen for | `gemma_test_mission` |
| `--namespace` | Target queue namespace | `default` |
| `--node` | Unique identifier for this worker | `worker-1` |
| `--model` | LLM string (provider/model format) | `gemini/gemma-4-31b-it` |
| `--prompt` | System prompt for the agent | *See code* |
| `--caps` | Comma-separated worker capabilities | `gemma,termux-isolated` |
| `--timeout` | Max execution time in seconds | `900` |
| `--verbosity`| Log level (`DEBUG`, `INFO`, `SILENT`) | `INFO` |
| `--dashboard`| Chiasm dashboard URL | `None` |
| `--profile` | Path to JSON/YAML config file | `None` |
| `--fast` | Override model to `gemini-2.5-flash` | `False` |
| `--ping` | Run health check and exit | `False` |
| `--api-base` | Custom OpenAI-compatible API base URL (e.g., OpenRouter, Groq, Ollama) | `None` |

## Troubleshooting & Diagnostics
**1. API Key Not Found:** Ensure your `~/.apikey` or `~/.<provider>key` does not have hidden newline characters.

**2. Missions Sticking in Queue:** Check if the worker's `--goal` and `--namespace` perfectly match the publisher's payload.

**3. Timeout Errors:** Increase `--timeout` if tasks require heavy network latency or slow tools.
