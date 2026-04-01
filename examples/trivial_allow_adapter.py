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
