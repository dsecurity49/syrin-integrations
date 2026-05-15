import os
import sys
from intent_bus import IntentClient
from pathlib import Path

def _get_key():
    path = Path.home() / ".apikey"
    if not path.exists():
        print("🔴 Missing ~/.apikey")
        sys.exit(1)
    return path.read_text().strip()

def main():
    print("\n\033[96m=== SYRIN STRESS TEST IGNITED ===\033[0m")
    client = IntentClient(api_key=_get_key())
    
    num_missions = 10
    print(f"Publishing {num_missions} concurrent missions to 'default/gemma_test_mission'...")
    
    for i in range(1, num_missions + 1):
        try:
            # We give the AI a very strict, easily verifiable task
            payload = {"instruction": f"Perform a system check. Reply with exactly this string and nothing else: 'STATUS_GREEN_MISSION_{i}'"}
            
            client.publish(
                goal="gemma_test_mission",
                payload=payload,
                namespace="default"
            )
            print(f"  → Mission {i} injected successfully.")
        except Exception as e:
            print(f"  ❌ Failed to inject Mission {i}: {e}")
            
    print("\n\033[92mAll missions published. Switch to your worker terminal and watch the queue!\033[0m\n")

if __name__ == "__main__":
    main()
