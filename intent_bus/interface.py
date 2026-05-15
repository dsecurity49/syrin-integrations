import json
import logging
from pathlib import Path
from intent_bus import IntentClient

# Mute noisy internal logs
logging.getLogger("urllib3").setLevel(logging.WARNING)

def load_secret(filename: str) -> str:
    path = Path.home() / filename
    if path.exists(): 
        return path.read_text().strip()
    raise FileNotFoundError(f"Missing secret: {path}")

def main():
    print("\n\033[95m=== INTENT BUS COMMAND LINE INTERFACE ===\033[0m")
    print("Connecting to the broker...")

    try:
        bus_key = load_secret(".apikey")
        client = IntentClient(api_key=bus_key)
        print("\033[92m[Connected]\033[0m Ready to dispatch missions to Gemma 4.\n")
    except Exception as e:
        print(f"\033[91m[Connection Error]\033[0m {e}")
        return

    # The Interactive Loop
    while True:
        try:
            # 1. Get user input
            user_input = input("\n\033[96m[Mission Prompt]>\033[0m ").strip()
            
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit', 'clear']:
                print("Exiting interface...")
                break

            # 2. Package the intent
            payload = {"instruction": user_input}
            target_goal = "gemma_test_mission"

            print(f"  \033[90m-> Dispatching to '{target_goal}'...\033[0m")

            # 3. Publish to the bus
            response = client.publish(
                goal=target_goal,
                payload=payload,
                namespace="default" 
            )

            print("  \033[92m-> Mission successfully dropped on the bus!\033[0m")
            print("  \033[90m-> Check your Worker terminal for execution logs.\033[0m")

        except KeyboardInterrupt:
            print("\nExiting interface...")
            break
        except Exception as e:
            print(f"\n  \033[91m[Dispatch Error]\033[0m {e}")

if __name__ == "__main__":
    main()
