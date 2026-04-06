#!/usr/bin/env python3
"""
Recalculate scenario difficulty tiers empirically based on actual adapter results.

Reads multiple v1 output directories, computes per-scenario failure rate across
adapters, and assigns difficulty based on how many adapters got it wrong.

- easy: all adapters get it right (0% failure)
- moderate: 1-2 adapters get it wrong (1-50% failure)
- hard: 3+ adapters get it wrong (51%+ failure)

Usage:
    python3 scripts/recalculate_difficulty.py outputs/v1_cliniclaw outputs/v1_openai_guardrails ...
"""
import json
import os
import sys
from pathlib import Path
from collections import defaultdict

SCENARIO_DIR = Path(__file__).parent.parent / "scenarios" / "healthcare_core_v0"


def load_report(output_dir: str) -> dict:
    """Load report.json and return per-scenario policy results."""
    report_path = Path(output_dir) / "report.json"
    if not report_path.exists():
        print(f"Warning: {report_path} not found, skipping")
        return {}
    with open(report_path) as f:
        report = json.load(f)
    results = {}
    for s in report.get("per_scenario", []):
        sid = s["scenario_id"]
        # Policy compliance: 1 = correct, 0 = wrong, None = not tested
        pol = s.get("policy_compliance")
        if pol is not None:
            results[sid] = pol == 1
    return results


def main():
    if len(sys.argv) < 2:
        # Auto-discover v1 output directories
        outputs = Path(__file__).parent.parent / "outputs"
        dirs = sorted(d for d in outputs.iterdir() if d.name.startswith("v1_") and (d / "report.json").exists())
        if not dirs:
            print("No v1 output directories found. Run benchmarks first.")
            sys.exit(1)
        print(f"Auto-discovered {len(dirs)} v1 output directories:")
        for d in dirs:
            print(f"  {d.name}")
    else:
        dirs = [Path(d) for d in sys.argv[1:]]

    # Load results from each adapter
    adapter_results = {}
    for d in dirs:
        name = d.name
        results = load_report(str(d))
        if results:
            adapter_results[name] = results
            print(f"  {name}: {len(results)} scenario results loaded")

    if not adapter_results:
        print("No results to process.")
        sys.exit(1)

    # Compute per-scenario failure rate
    scenario_failures = defaultdict(lambda: {"fail": 0, "total": 0})
    for adapter_name, results in adapter_results.items():
        for sid, correct in results.items():
            scenario_failures[sid]["total"] += 1
            if not correct:
                scenario_failures[sid]["fail"] += 1

    # Assign difficulty based on failure rate
    difficulty_map = {}
    for sid, stats in scenario_failures.items():
        rate = stats["fail"] / stats["total"] if stats["total"] > 0 else 0
        if rate == 0:
            difficulty_map[sid] = "easy"
        elif rate <= 0.5:
            difficulty_map[sid] = "moderate"
        else:
            difficulty_map[sid] = "hard"

    # Count changes
    changes = {"upgraded": 0, "downgraded": 0, "unchanged": 0}
    tier_order = {"easy": 0, "moderate": 1, "hard": 2}

    # Update scenario files
    files = sorted(f for f in os.listdir(SCENARIO_DIR) if f.endswith(".json"))
    counts = {"easy": 0, "moderate": 0, "hard": 0}
    type_counts = defaultdict(lambda: {"easy": 0, "moderate": 0, "hard": 0})

    for fname in files:
        path = SCENARIO_DIR / fname
        with open(path) as f:
            scenario = json.load(f)

        sid = scenario["id"]
        old_diff = scenario.get("difficulty", "moderate")

        if sid in difficulty_map:
            new_diff = difficulty_map[sid]
        else:
            # Scenario not tested by any adapter's policy dimension — keep existing
            new_diff = old_diff

        scenario["difficulty"] = new_diff

        with open(path, "w") as f:
            json.dump(scenario, f, indent=4)
            f.write("\n")

        counts[new_diff] += 1
        stype = scenario.get("scenario_type", "unknown")
        type_counts[stype][new_diff] += 1

        old_rank = tier_order.get(old_diff, 1)
        new_rank = tier_order.get(new_diff, 1)
        if new_rank > old_rank:
            changes["upgraded"] += 1
        elif new_rank < old_rank:
            changes["downgraded"] += 1
        else:
            changes["unchanged"] += 1

    print(f"\n=== Empirical Difficulty Assignment ===")
    print(f"Based on {len(adapter_results)} adapters")
    print(f"Total: {sum(counts.values())} scenarios")
    print(f"  Easy:     {counts['easy']}")
    print(f"  Moderate: {counts['moderate']}")
    print(f"  Hard:     {counts['hard']}")
    print(f"\nChanges from algorithmic assignment:")
    print(f"  Harder:    {changes['upgraded']}")
    print(f"  Easier:    {changes['downgraded']}")
    print(f"  Unchanged: {changes['unchanged']}")
    print(f"\nPer-type:")
    for stype in sorted(type_counts):
        tc = type_counts[stype]
        print(f"  {stype}: easy={tc['easy']} moderate={tc['moderate']} hard={tc['hard']}")


if __name__ == "__main__":
    main()
