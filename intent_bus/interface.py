import sys
import json
import logging
import argparse
from pathlib import Path
from intent_bus import IntentClient

logging.getLogger("urllib3").setLevel(logging.WARNING)

def load_secret(filename: str) -> str:
    path = Path.home() / filename
    return path.read_text().strip() if path.exists() else ""

def load_profile(profile_path: str) -> dict:
    p = Path(profile_path)
    if not p.exists():
        print(f"🔴 Fatal: Profile not found: {profile_path}")
        sys.exit(1)

    with open(p, "r") as f:
        if p.suffix == '.json':
            data = json.load(f)
        elif p.suffix in ['.yaml', '.yml']:
            try:
                import yaml
                data = yaml.safe_load(f)
            except ImportError:
                print("🟡 Warning: Cannot load YAML. Install pyyaml: pip install pyyaml")
                sys.exit(1)
        else:
            print("🔴 Fatal: Profile must be .json or .yaml")
            sys.exit(1)

    if not isinstance(data, dict):
        print("🔴 Fatal: Profile must be a valid JSON/YAML object.")
        sys.exit(1)
        
    return data

def main():
    parser = argparse.ArgumentParser(description="Interactive Intent Bus REPL")
    parser.add_argument("--goal", default="gemma_test_mission")
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--profile", help="Optional JSON/YAML profile")
    args = parser.parse_args()

    if args.profile:
        profile = load_profile(args.profile)
        args.goal = profile.get("goal", args.goal)
        args.namespace = profile.get("namespace", args.namespace)

    print("\n\033[95m=== INTENT BUS COMMAND LINE INTERFACE ===\033[0m")
    try:
        bus_key = load_secret(".apikey")
        if not bus_key: raise ValueError("Missing ~/.apikey")
        client = IntentClient(api_key=bus_key)
        print(f"\033[92m[Connected]\033[0m Target: {args.namespace}/{args.goal}\n")
    except Exception as e:
        print(f"\033[91m[Connection Error]\033[0m {e}")
        sys.exit(1)

    while True:
        try:
            user_input = input("\n\033[96m[Mission Prompt]>\033[0m ").strip()
            if not user_input: continue
            if user_input.lower() in ['exit', 'quit', 'clear']: break
            
            client.publish(goal=args.goal, payload={"instruction": user_input}, namespace=args.namespace)
            print("  \033[92m-> Mission successfully dropped on the bus!\033[0m")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n  \033[91m[Dispatch Error]\033[0m {e}")

if __name__ == "__main__":
    main()
