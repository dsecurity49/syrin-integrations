# Advanced Architecture & Examples

## Complete Working Example

**1. Create a specific profile (`examples/profiles/summarizer.json`):**
```json
{
  "node": "text-bot-01",
  "goal": "summarize_text",
  "namespace": "content",
  "model": "gemini/gemini-3.1-flash-lite",
  "prompt": "You are a summarization bot. Return 3 bullet points."
}
```

**2. Boot the Worker in Terminal A:**
```bash
python worker.py --profile examples/profiles/summarizer.json
```

**3. Dispatch the Mission in Terminal B:**
```bash
python trigger.py "The history of the Roman Empire is vast and spans across..." --profile examples/profiles/summarizer.json
```

**4. Result in Terminal A:**
```text
[8a12f9b1] [text-bot-01] [CLAIMED] MISSION RECEIVED: The history of the Roman Empire is vast and spans...
[8a12f9b1] [text-bot-01] 🟢 MISSION COMPLETE.
* The Roman Empire spanned multiple continents.
* It had a complex political structure.
* It eventually fell due to internal and external pressures.
```

## Profile Deep-Dive
Profiles drive the CLI parameters cleanly. Let's look at `researcher.json`:
* `"goal": "deep_research"`: The worker only picks up jobs explicitly tagged for `deep_research`.
* `"namespace": "analytics"`: Keeps this queue completely isolated from default traffic.
* `"model": "gemini/gemini-3.1-pro-preview"`: Selects the heavy-duty model for this specific node.
* `"timeout": 3600`: Overrides the 15-minute default to allow 1 hour of research time.

## Multi-Worker Orchestration
You can scale horizontally by running multiple terminal sessions (or containers).
* **Worker 1:** `python worker.py --node w-1`
* **Worker 2:** `python worker.py --node w-2`
* **Worker 3:** `python worker.py --node w-3`

When you dispatch 3 missions via `trigger.py`, the Intent Bus guarantees **Atomic Claims**. Worker 1 takes Mission A, Worker 2 takes Mission B, and Worker 3 takes Mission C. Workers atomically claim jobs, preventing concurrent double-execution.

## State Recovery Walkthrough
Syrin supports resuming long tasks.
1. Dispatch a long mission (e.g., writing a 10-page essay).
2. Look for `[[STATE]] Syncing state to KV store...` in the worker terminal.
3. **Kill the worker** (`Ctrl+C`). The Intent Bus drops the claim after 60 seconds.
4. Restart the worker.
5. Watch the log: `[🟡 [State Warning] Recovered previous checkpoint]`. The agent resumes writing from where it was killed rather than starting over.

## Universal Model Support (OpenRouter, Groq, Local Models)

Syrin's built-in OpenAI wrapper acts as a **universal adapter**. By providing a custom `api_base` in your profile, you can route missions to any OpenAI-compatible API, including local offline models and open-weights hosts.

**Example 1: OpenRouter (Thousands of Open-Source Models)**
```json
{
  "node": "openrouter-researcher",
  "api_base": "https://openrouter.ai/api/v1",
  "model": "openrouter/meta-llama/llama-3.3-70b-instruct",
  "prompt": "You are a research agent...",
  "caps": "research,web-search",
  "timeout": 900
}
```

**Example 2: Groq (Ultra-Fast Inference)**
```json
{
  "node": "groq-reviewer",
  "api_base": "https://api.groq.com/openai/v1",
  "model": "groq/llama-3.1-8b-instant",
  "prompt": "You are a senior DevOps engineer...",
  "caps": "code-review",
  "timeout": 300
}
```

**Example 3: Local / Offline Edge Models (Ollama)**
```json
{
  "node": "local-edge-node",
  "api_base": "http://localhost:11434/v1",
  "model": "local/deepseek-coder",
  "prompt": "You are an offline coding assistant...",
  "caps": "python,offline",
  "timeout": 1200
}
```
*Note: Make sure to export the corresponding API key (e.g., `OPENROUTER_API_KEY` or `GROQ_API_KEY`) in your environment or hidden dotfiles before starting the worker.*

## Links
* [Intent Bus Server Repo](https://github.com/dsecurity49/Intent-Bus)
