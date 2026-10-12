---
name: alphagsm-server-enablement
description: "Use when fixing disabled or skipped game servers and closing AlphaGSM support tracker backlog items."
---

# Enable a server

Before reproducing a lifecycle, assess the selected game with [server-requirements](../alphagsm-server-requirements/SKILL.md) and apply its [approval gates](../alphagsm-server-requirements/references/approval-gates.md). Prefer repository Docker environments, ask on first use and wait for approval of any new host/manager/image/test dependency. A failing integration test is no permission to install prerequisites silently.

Read [disabled-server-gate](../disabled-server-gate/SKILL.md), [TEST_STATUS](../../docs/TEST_STATUS.md), [public support tracker](../../docs/game-server-support.md), matching guide and integration test. Identify canonical id/aliases and the evidence behind the current disabled/skip state. Record any local campaign checklist so it can be closed in the same change.

Reproduce the failing AlphaGSM lifecycle. Read diagnostic log tail, last query error, actual runtime/config/start flags, download/provisioning and query address. Search official upstream docs/issues before accepting that a game cannot run. Use [test-triage](../alphagsm-test-triage/SKILL.md) for timeouts; never disable a game to hide slow startup or a readiness failure.

Fix shared helpers at the root cause where appropriate. Prove create/setup/start/readiness/status/query/info/info JSON/stop and shutdown through AlphaGSM. Source hibernation/TCP fallback is insufficient. Follow [runtime-validation](../alphagsm-runtime-validation/SKILL.md) for container-capable paths using branch-local images.

Promote only the support class that the evidence proves: PASSED for fully validated self-provisioning; ENABLED (AUTH) for supported provider-backed prerequisites; ENABLED (BYO) for owned assets/exports/URLs/local services. Align enabled_auth/enabled_byo configs, disabled creation gate, test skip wording, TEST_STATUS and guide. Run the support-tracker generator/check according to its help; do not hand-edit generated output inconsistently.

Example: an integration timeout caused by the wrong query port is a repair plus passing lifecycle and tracker update. It is not a skip. If the upstream service is genuinely retired, record specific source/log evidence and the remaining blocker so later agents do not repeat the investigation. Update changelog and mark proven campaign tasks done.
