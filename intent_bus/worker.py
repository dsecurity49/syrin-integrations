import os
import sys
import json
import urllib.request
import logging
import argparse
from pathlib import Path

# --- Framework Integrations ---
from intent_bus import IntentClient
from intent_bus_syrin import IntentBusSyrinHarness, ChiasmObserver, configure_observability
from syrin import Agent
from syrin.model import Model

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ==============================================================================
# SECRETS & DIAGNOSTICS
# ==============================================================================

def _resolve_secret(env_var: str, file_name: str) -> str:
    """Fetches secrets from the environment or hidden home directory files."""
    if env_var in os.environ: return os.environ[env_var].strip()
    path = Path.home() / file_name
    if path.exists(): return path.read_text().strip()
    return ""

def _run_diagnostics(args, bus_key: str, provider: str, active_key: str, chiasm_key: str):
    """Executes a rapid health check of the environment and exits."""
    print(f"\n\033[95m=== SYRIN WORKER HEALTH CHECK [{args.node}] ===\033[0m")

    if bus_key: print("✅ Intent Bus API Key found.")
    else: print("❌ Missing Intent Bus Key (~/.apikey)")

    if active_key: print(f"✅ {provider.upper()} API Key found.")
    else: print(f"❌ Missing API Key for '{provider}'. Check your hidden key files.")

    if args.dashboard:
        if not args.dashboard.startswith(("http://", "https://")):
            print("❌ Dashboard URL must start with http:// or https://")
            sys.exit(1)
        if not chiasm_key:
            print("❌ Dashboard URL provided, but missing Chiasm Key (~/.chiasmkey)")
            sys.exit(1)
        try:
            req = urllib.request.Request(f"{args.dashboard.rstrip('/')}/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    print(f"✅ Dashboard reachable ({args.dashboard})")
                else:
                    print(f"⚠️ Dashboard responded with unexpected status: {response.status}")
        except Exception as e:
            print(f"❌ Dashboard unreachable: {e}")
    else:
        print("➖ Dashboard telemetry disabled (No URL provided)")

    print("\nDiagnostic complete. Exiting.\n")
    sys.exit(0)

# ==============================================================================
# CORE WORKER INITIALIZATION
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Syrin AI Intent Worker Node")

    parser.add_argument("--goal", type=str, default="gemma_test_mission", help="The Intent Bus goal to claim")
    parser.add_argument("--namespace", type=str, default="default", help="The namespace queue")
    parser.add_argument("--node", type=str, default="worker-1", help="Unique identifier for this worker instance")

    parser.add_argument("--model", type=str, default="gemini/gemma-4-31b-it", help="The LLM model string (e.g., groq/llama3-8b, gemini/gemini-3.1-pro-preview)")
    parser.add_argument("--prompt", type=str, default="You are a helpful AI assistant executing operations.", help="AI system prompt")
    parser.add_argument("--caps", type=str, default="gemma,termux-isolated", help="Comma-separated capabilities")

    parser.add_argument("--timeout", type=int, default=900, help="Maximum execution time in seconds")
    parser.add_argument("--verbosity", type=str, choices=["DEBUG", "INFO", "SILENT"], default="INFO", help="Console output level")
    parser.add_argument("--dashboard", type=str, help="Chiasm UI endpoint (e.g., 'http://localhost:4300')")

    parser.add_argument("--profile", type=str, help="Load configuration from a JSON/YAML profile file")
    parser.add_argument("--fast", action="store_true", help="Instantly override model to gemini-2.5-flash for rapid testing")
    parser.add_argument("--ping", action="store_true", help="Run a health check on keys and network, then exit")

    args = parser.parse_args()

    if args.profile:
        profile_path = Path(args.profile)
        if profile_path.exists():
            profile_data = {}
            if profile_path.suffix in ['.yaml', '.yml']:
                try:
                    import yaml
                    with open(profile_path, 'r') as f:
                        profile_data = yaml.safe_load(f) or {}
                except ImportError:
                    print(f"🟡 Warning: Cannot load {args.profile}. Run 'pip install pyyaml' for YAML support.")
                    sys.exit(1)
            elif profile_path.suffix == '.json':
                with open(profile_path, 'r') as f:
                    profile_data = json.load(f)
            else:
                print("🔴 Fatal: Profile must be .json or .yaml")
                sys.exit(1)

            if not isinstance(profile_data, dict):
                print("🔴 Fatal: Profile must be a JSON/YAML object (got dict/list/string)")
                sys.exit(1)

            for key, value in profile_data.items():
                if hasattr(args, key):
                    setattr(args, key, value)
            print(f"📂 Loaded profile: {args.profile}")
        else:
            print(f"🔴 Fatal: Profile file {args.profile} not found.")
            sys.exit(1)

    if args.fast:
        args.model = "gemini/gemini-2.5-flash"
        args.verbosity = "DEBUG"
        print("⚡ FAST MODE: Model overridden to gemini-2.5-flash (Verbosity set to DEBUG)")

    provider = args.model.split("/")[0] if "/" in args.model else "openai"

    bus_key = _resolve_secret("INTENT_BUS_KEY", ".apikey")
    chiasm_key = _resolve_secret("CHIASM_KEY", ".chiasmkey")

    provider_keys = {
        "gemini": _resolve_secret("GEMINI_API_KEY", ".geminikey"),
        "google": _resolve_secret("GEMINI_API_KEY", ".geminikey"),
        "openai": _resolve_secret("OPENAI_API_KEY", ".openaikey"),
        "anthropic": _resolve_secret("ANTHROPIC_API_KEY", ".claudekey"),
        "groq": _resolve_secret("GROQ_API_KEY", ".groqkey"),
        "openrouter": _resolve_secret("OPENROUTER_API_KEY", ".openrouterkey")
    }

    active_key = provider_keys.get(provider, _resolve_secret(f"{provider.upper()}_API_KEY", f".{provider}key"))

    if args.ping:
        _run_diagnostics(args, bus_key, provider, active_key, chiasm_key)

    if not bus_key:
        print("🔴 Fatal: Missing Intent Bus API Key. Create ~/.apikey or use --ping to diagnose.")
        sys.exit(1)
    if not active_key:
        print(f"🔴 Fatal: Missing API key for '{provider}'. Check your hidden key files or use --ping.")
        sys.exit(1)

    configure_observability(args.verbosity)
    capabilities_list = [cap.strip() for cap in args.caps.split(",")]

    os.environ[f"{provider.upper()}_API_KEY"] = active_key

    bus_client = IntentClient(api_key=bus_key)
    observer = ChiasmObserver(chiasm_url=args.dashboard, api_key=chiasm_key, node_name=args.node) if args.dashboard else None

    # --- Dynamic Agent Factory ---
    def agent_factory():
        # Syrin requires explicit Model wrappers. We dynamically route based on the provider string.
        if provider in ["gemini", "google"]:
            syrin_model = Model.Google(args.model, api_key=active_key)
        elif provider == "anthropic":
            syrin_model = Model.Anthropic(args.model, api_key=active_key)
        else:
            # Groq, OpenRouter, and OpenAI all use the OpenAI standard under the hood
            syrin_model = Model.OpenAI(args.model, api_key=active_key)

        return Agent(
            model=syrin_model,
            system_prompt=args.prompt,
            debug=(args.verbosity == "DEBUG")
        )

    harness = IntentBusSyrinHarness(
        agent_factory=agent_factory,
        bus=bus_client,
        capabilities=capabilities_list,
        telemetry_filter={"run_end", "error", "tool_call", "checkpoint_ready"},
        observer=observer,
        mission_timeout=args.timeout,
        node_name=args.node
    )

    print(f"\n--- SYRIN SUBSTRATE RUNTIME v7.0 ---")
    print(f" Node:         {args.node}")
    print(f" Listening:    {args.namespace} / {args.goal}")
    print(f" Capabilities: {capabilities_list}")
    print(f" Model Engine: {args.model}")
    print(f" Verbosity:    {args.verbosity}\n")

    harness.serve(goal=args.goal, namespace=args.namespace)

if __name__ == "__main__":
    main()
