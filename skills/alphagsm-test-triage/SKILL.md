---
name: alphagsm-test-triage
description: "Use when diagnosing AlphaGSM lint, unit, integration, smoke or CI failures from actual diagnostics."
---

# Triage tests

Inputs: failing command/CI job, checkout revision, full traceback/log tail and environment. Reproduce with the repository's pinned dependencies and the same test runner before changing implementation. Distinguish an environment mismatch from a repository defect; preserve baseline evidence.

```bash
make lint
make test
make integration-test IT_TEST=test_tf2.py
make smoke-test SMOKE_TEST=run_tf2.sh
```

Select the relevant command rather than starting all download-heavy tests. Integration needs ALPHAGSM_WORK_DIR and its opt-in/download requirements; sandboxed local socket/process tests may require their normal host permissions. A wrong similarly named crontab package can break CronTab APIs: inspect imported path/version before patching working code.

For timeout failures, read the wait helpers' diagnostic 150-line tail and last query error. Check download outcome, executable crash, missing runtime/config/auth, readiness marker and query address/protocol. Research official upstream docs/issues for uncertain prerequisites. Increase a deadline only when observed startup/download progress justifies it. Never add timeout skips or disabled entries to hide failures.

Example: “Server is hibernating” appears before A2S timeout. Reproduce the real protocol path, inspect keep-awake settings and hooks, then rerun the same lifecycle. A log marker or TCP fallback is not a substitute.

Write the smallest regression covering the root cause, run it failing before the fix, then pass it and required affected checks. Avoid broad repeated runs after evidence is already sufficient. Report command/exit/results and unverified limitations. Use [runtime-validation](../alphagsm-runtime-validation/SKILL.md) for backend-family failures and [server-enablement](../alphagsm-server-enablement/SKILL.md) when status changes.
