"""Trivial anti-baseline adapter: always allows with no audit trail.
Used to establish the inverse floor — scores 100% on allow scenarios, 0% on deny scenarios."""
import json, sys

def handle(scenario):
    return {
        "decision": "allow",
        "audit_entries": [],
        "execution_halted": False,
        "human_notified": False,
        "output_content": scenario.get("input_content"),
    }

if __name__ == "__main__":
    scenario = json.loads(sys.stdin.read())
    print(json.dumps(handle(scenario)))
