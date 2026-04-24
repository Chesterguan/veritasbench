#!/usr/bin/env python3
"""
run_model.py — resolve a provider short-name, set env, run the benchmark.

Usage:
    python scripts/run_model.py <short-name>
        [--suite healthcare_v1]
        [--output outputs/llm_<short_name>]
        [--retries 2] [--timeout 30000]
        [--dry-run]

Examples:
    python scripts/run_model.py gpt-4o-mini
    python scripts/run_model.py deepseek-r1 --timeout 60000
    python scripts/run_model.py huatuogpt-o1 --dry-run
"""
import argparse
import os
import pathlib
import shlex
import subprocess
import sys

import yaml


REPO = pathlib.Path(__file__).resolve().parents[1]
PROVIDERS = REPO / "examples" / "providers.yaml"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("short_name", help="Provider short name from examples/providers.yaml")
    parser.add_argument("--suite", default="healthcare_v1")
    parser.add_argument("--output", default=None, help="Defaults to outputs/llm_<short_name_underscore>")
    parser.add_argument("--retries", default="2")
    parser.add_argument("--timeout", default="30000")
    parser.add_argument("--dry-run", action="store_true", help="Print the cargo command without executing")
    args = parser.parse_args()

    with open(PROVIDERS) as f:
        providers = yaml.safe_load(f)

    if args.short_name not in providers:
        print(
            f"run_model: unknown provider short-name '{args.short_name}'. "
            f"Known: {sorted(providers)}",
            file=sys.stderr,
        )
        return 2

    cfg = providers[args.short_name]
    key_env = cfg["key_env"]
    if not os.environ.get(key_env):
        print(
            f"run_model: {key_env} environment variable is not set "
            f"(required for '{args.short_name}'). "
            f"Set it in your .env file (see .env.example).",
            file=sys.stderr,
        )
        return 3

    env = os.environ.copy()
    for k, v in cfg["env"].items():
        env[k] = str(v)
    # llm_openai_compat.py reads OPENAI_API_KEY; copy the provider key into it.
    if cfg["adapter"] == "llm_openai_compat.py":
        env["OPENAI_API_KEY"] = os.environ[key_env]

    output_dir = args.output or f"outputs/llm_{args.short_name.replace('-', '_')}"

    cargo_cmd = [
        "cargo", "run", "--release", "-p", "veritasbench-cli", "--",
        "run",
        "--adapter", cfg["adapter"],
        "--suite", args.suite,
        "--output", output_dir,
        "--retries", str(args.retries),
        "--timeout", str(args.timeout),
    ]

    if args.dry_run:
        print(" ".join(shlex.quote(x) for x in cargo_cmd))
        print(f"# env overrides: {cfg['env']}")
        print(f"# key_env: {key_env}")
        return 0

    print(f"run_model: invoking {args.short_name} → {output_dir}", file=sys.stderr)
    return subprocess.call(cargo_cmd, cwd=REPO, env=env)


if __name__ == "__main__":
    sys.exit(main())
