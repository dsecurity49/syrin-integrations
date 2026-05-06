"""Build a preview-first platform-hosted launch request for a Syrin agent.

Run:
    python agoragentic/starter_kits/platform_hosted_syrin_agent/launch_request.py
    python agoragentic/starter_kits/platform_hosted_syrin_agent/launch_request.py --provider aws_apprunner --source-type repository --source-ref https://github.com/example/syrin-agent --review-action provision
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        """Allow offline tests to import this example without python-dotenv."""
        return False

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agoragentic.starter_kits.platform_hosted_syrin_agent.config import (
    build_runtime_profile,
    build_startup_notes,
    build_system_prompt,
)
from agoragentic.starter_kits.platform_hosted_syrin_agent.deployment import build_platform_hosted_deployment
from agoragentic.starter_kits.platform_hosted_syrin_agent.reviewed_executor import (
    review_hosted_deployment_action,
)


def _parse_secret_ref(raw: str) -> dict[str, str]:
    """Parse one ENV=SECRET_ID pair into a vault handoff reference."""
    env_name, sep, secret_id = raw.partition("=")
    if not sep or not env_name.strip() or not secret_id.strip():
        raise argparse.ArgumentTypeError("secret refs must look like ENV_NAME=secret_reference")
    return {
        "type": "reference",
        "env_name": env_name.strip(),
        "secret_id": secret_id.strip(),
    }


def _build_parser() -> argparse.ArgumentParser:
    """Create CLI arguments for the platform-hosted launch request."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent_name", nargs="?", default="Platform Hosted Syrin Agent", help="Agent display name.")
    parser.add_argument("--provider", default=os.getenv("PLATFORM_HOSTED_PROVIDER", "simulated"), help="Hosted provider lane.")
    parser.add_argument("--source-type", default="repository", choices=("repository", "container_image"), help="Hosted deployment source type.")
    parser.add_argument("--source-ref", default="https://github.com/example/syrin-agent", help="Repository URL or container image ref.")
    parser.add_argument("--goal", default="Launch a hosted Syrin agent safely with reviewed execution and preview-first provider contracts.", help="Primary deployment goal.")
    parser.add_argument("--publish-listing", action="store_true", help="Include listing activation intent in the launch contract.")
    parser.add_argument("--service-url", default="", help="Optional attached service URL for smoke or activation previews.")
    parser.add_argument("--secret-ref", action="append", default=[], type=_parse_secret_ref, help="ENV_NAME=secret_reference pair for vault handoff previews.")
    parser.add_argument("--review-action", choices=("provision", "smoke", "activate", "self_serve_launch"), help="Optional hosted action to review against the current gate state.")
    return parser


def main() -> None:
    """Build and print the platform-hosted launch preview."""
    load_dotenv(ROOT / "agoragentic" / ".env", override=False)
    load_dotenv(ROOT / "agoragentic" / "starter_kits" / "platform_hosted_syrin_agent" / ".env", override=False)

    args = _build_parser().parse_args()
    profile_env = dict(os.environ)
    profile_env["PLATFORM_HOSTED_PROVIDER"] = args.provider
    if args.service_url:
        profile_env["PLATFORM_HOSTED_SERVICE_URL"] = args.service_url
    profile = build_runtime_profile(profile_env)
    deployment = build_platform_hosted_deployment(
        profile=profile,
        agent_name=args.agent_name,
        source_type=args.source_type,
        source_ref=args.source_ref,
        goal=args.goal,
        publish_listing=args.publish_listing,
        secret_references=args.secret_ref,
    )

    payload = {
        "startup_notes": list(build_startup_notes(profile)),
        "system_prompt": build_system_prompt(profile),
        "deployment": deployment,
    }
    if args.review_action:
        payload["review"] = review_hosted_deployment_action(
            deployment=deployment,
            agent_id=deployment["agent_id"],
            action_key=args.review_action,
            body={"publish_listing": args.publish_listing},
        )

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
