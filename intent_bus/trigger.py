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
        data = None
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Intent Bus Mission Trigger")
    parser.add_argument("instruction", help="Mission instruction")
    parser.add_argument("--goal", default="gemma_test_mission")
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--profile", help="Optional JSON/YAML profile")
    args = parser.parse_args()

    if args.profile:
        profile = load_profile(args.profile)
        args.goal = profile.get("goal", args.goal)
        args.namespace = profile.get("namespace", args.namespace)

    try:
        api_key = load_secret(".apikey")
        if not api_key:
            print("🔴 Fatal: Missing ~/.apikey")
            sys.exit(1)
            
        client = IntentClient(api_key=api_key)
        status = client.publish(
            goal=args.goal,
            payload={"instruction": args.instruction},
            namespace=args.namespace
        )
        print(f"Mission dispatched [{args.namespace}/{args.goal}] | ID: {status.id}")
    except Exception as e:
        print(f"Failed to dispatch: {e}")
        sys.exit(1)
