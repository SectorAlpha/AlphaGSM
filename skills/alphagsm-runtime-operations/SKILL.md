---
name: alphagsm-runtime-operations
description: "Use when selecting or diagnosing process versus Docker execution for an existing AlphaGSM server."
---

# Operate a runtime

Resolve [execution context](../alphagsm-agent-operations/references/execution-context.md), then inspect:

```bash
alphagsm mymc doctor --json
alphagsm mymc set --list
```

Read [host Docker](../../docs/docker-runtime-host.md) or [manager Docker](../../docs/docker-manager.md) according to the actual installation. The host daemon owns mounts; a manager container needs paths visible to that daemon. Capture configured backend, effective engine/family/image, install path, published ports and container state. A configured Docker preference alone does not prove effective Docker execution.

Use supported schema keys and the existing runtime configuration for changes. The current global backend forces process when it is not docker; when docker is selected, module runtime requirements determine the effective engine and can override stored runtime edits. `set runtime` is not a reliable per-tag engine selector. Resolve effective metadata against `src/server/runtime.py`; do not invent a `runtime` command. If the requested single-tag switch needs a global change affecting other tags, establish that scope or report the isolation limit. Stop affected servers before an authorized backend change and preserve its data/port ownership.

Prefer the in-repo image scaffold and branch-local build for development validation. For Windows-only servers on Linux, follow the shared wine-proton contract rather than creating ad hoc Wine launchers. A missing Docker daemon/image/mount is diagnosed from doctor and runtime logs; bound retries to one attempted correction per identified cause.

Launch with AlphaGSM start and verify the effective runtime plus real protocol health. Finish with [evidence](../alphagsm-agent-operations/references/evidence-and-handoff.md). Use [runtime-validation](../alphagsm-runtime-validation/SKILL.md) for repository contracts and representative matrix changes.
