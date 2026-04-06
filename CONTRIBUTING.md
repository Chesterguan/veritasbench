# Contributing to VeritasBench

## Submit a better adapter

The most impactful contribution: **write an adapter for your framework and submit a PR.**

The included adapters use frameworks at their simplest -- minimal configuration, generic prompts, basic setup. If you know a framework well, you can almost certainly write a more representative adapter. We'll run it against all 700 scenarios and publish the results.

### How to contribute an adapter

1. Fork the repo and create `examples/<your_framework>.py`
2. Follow the [Adapter Protocol](docs/adapter-protocol.md)
3. Validate: `cargo run -p veritasbench-cli -- validate --adapter examples/<your_framework>.py`
4. Run the benchmark: `cargo run -p veritasbench-cli -- run --adapter examples/<your_framework>.py --suite healthcare_core_v0 --output outputs/<your_framework>`
5. For a harder test, run with `--blind` to strip scenario_type from adapter input.
6. Include the report output in your PR description
7. Submit a PR

### What makes a good adapter

- **Use the real framework.** Don't simulate it. If you're writing an OpenAI Guardrails adapter, actually use the OpenAI Agents SDK.
- **Use a reasonable configuration.** Not the minimal possible, not an unrealistically tuned setup. What a competent developer would deploy.
- **Document your setup.** What packages, what configuration, what model, what version.
- **Be honest about limitations.** If your framework can't produce structured audit entries, return empty `audit_entries`. Don't fake traceability.

### What we'll do

- Run the adapter against all 700 scenarios
- Publish the results alongside existing adapters
- Credit you in the README and adapter file
- Not editorialize about the results -- the numbers speak for themselves

## Add scenarios

Want to test a governance property we're missing? Add scenario JSON files to `scenarios/healthcare_core_v0/`.

The benchmark covers 11 scenario types: Unauthorized Access, Missing Approval, Missing Justification, PHI Leakage, Unsafe Action Sequence, Emergency Override, Consent Management, Conflicting Authority, Incomplete Information, System-Initiated, and Accountability Gap.

Run `cargo run -p veritasbench-cli -- schema` to generate the JSON Schema for reference.

Requirements:
- Follow the existing schema exactly
- Include both ALLOW and DENY scenarios for your type
- Include an `expected` field with the correct decision
- Test with at least one adapter to verify scoring

Scenarios are validated by multi-model LLM consensus. If you believe an expected decision is incorrect, open an issue with your reasoning.

## Report issues

If you think a scenario has a wrong expected answer, a scoring rule is unfair, or an adapter misrepresents a framework -- open an issue. We'd rather fix a mistake than defend it.

## Code changes

For changes to the Rust codebase:
- `cargo test` must pass (87 tests)
- `cargo clippy` must pass with no warnings
- Follow existing code patterns
- Don't add features without discussion in an issue first

## License

By contributing, you agree that your contributions are licensed under the Apache-2.0 license.
