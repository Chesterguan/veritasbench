import json, sys

def handle(scenario):
    return {
        "decision": "deny",
        "audit_entries": [{
            "timestamp": "2026-04-01T00:00:00Z",
            "actor": scenario["actor"]["role"],
            "action": scenario["action"]["verb"],
            "resource": scenario["action"]["target_resource"],
            "decision": "deny",
            "reason": "baseline: deny all"
        }],
        "execution_halted": False,
        "human_notified": False,
        "output_content": None,
    }

if __name__ == "__main__":
    scenario = json.loads(sys.stdin.read())
    print(json.dumps(handle(scenario)))
