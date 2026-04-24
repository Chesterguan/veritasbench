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
from urllib.parse import urlparse

import yaml


REPO = pathlib.Path(__file__).resolve().parents[1]
PROVIDERS = REPO / "examples" / "providers.yaml"

# Env vars from the outer shell that we propagate into the adapter subprocess.
# Anything not on this list is dropped — so one adapter can't silently read
# another provider's API key out of os.environ.
SYSTEM_ENV_ALLOWLIST = {
    # basic process + locale
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "PWD", "TMPDIR", "TEMP", "TMP",
    "LANG", "LC_ALL", "LC_CTYPE", "LC_COLLATE", "LC_MESSAGES",
    # python / venv discovery
    "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYENV_VERSION", "PYENV_ROOT",
    # TLS trust store (needed by httpx/requests for HTTPS)
    "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE",
    # standard proxy vars — dropping these could silently break corp networks
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
    "http_proxy", "https_proxy", "no_proxy",
}

# Hosts we refuse to point an adapter at even over HTTPS — these are cloud
# metadata services and would exfiltrate credentials on SSRF.
BLOCKED_HOSTS = {
    "169.254.169.254",           # AWS / GCP / Azure IMDS
    "fd00:ec2::254",             # AWS IMDS IPv6
    "metadata.google.internal",  # GCP
    "metadata.goog",             # GCP alt
}

# Hosts we allow plain HTTP to (local inference servers like Ollama).
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _validate_base_url(url: str, short_name: str) -> None:
    """Reject base URLs that could leak the provider key. Only https://,
    or http:// when the host is a loopback address (local Ollama)."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in BLOCKED_HOSTS:
        raise ValueError(
            f"provider '{short_name}' has base_url pointing at a cloud "
            f"metadata service ({url}); refusing to run."
        )
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and host in LOOPBACK_HOSTS:
        return
    raise ValueError(
        f"provider '{short_name}' has disallowed base_url scheme "
        f"'{parsed.scheme}' for '{url}'. Only https:// or http://localhost "
        f"(local inference) is permitted."
    )


def _build_scoped_env(cfg: dict, short_name: str) -> dict:
    """Build a scrubbed env dict for the adapter subprocess. Only the single
    provider key declared in cfg['key_env'] is passed through; all other
    *_API_KEY / *_TOKEN / secret-looking vars are dropped."""
    env: dict = {k: v for k, v in os.environ.items() if k in SYSTEM_ENV_ALLOWLIST}

    # Provider config env (base url, model slug, region, etc.)
    for k, v in (cfg.get("env") or {}).items():
        env[k] = str(v)

    # Single provider key this adapter is allowed to see. Callers reaching
    # this helper from outside main() should already have validated the key;
    # raise a clear error rather than a bare KeyError if they didn't.
    key_env = cfg["key_env"]
    key_value = os.environ.get(key_env)
    if not key_value:
        raise ValueError(
            f"provider '{short_name}' requires {key_env} but it is not set in the environment"
        )
    env[key_env] = key_value

    # llm_openai_compat.py reads OPENAI_API_KEY; alias the provider key so the
    # adapter doesn't need to know which provider it's pointed at.
    if cfg["adapter"] == "llm_openai_compat.py" and key_env != "OPENAI_API_KEY":
        env["OPENAI_API_KEY"] = key_value

    return env


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

    if not isinstance(providers, dict) or not providers:
        print("run_model: providers.yaml is empty or malformed", file=sys.stderr)
        return 2

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

    # Validate any base_url in config — SSRF guard.
    base_url = (cfg.get("env") or {}).get("OPENAI_BASE_URL")
    if base_url:
        try:
            _validate_base_url(base_url, args.short_name)
        except ValueError as e:
            print(f"run_model: {e}", file=sys.stderr)
            return 4

    env = _build_scoped_env(cfg, args.short_name)

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
