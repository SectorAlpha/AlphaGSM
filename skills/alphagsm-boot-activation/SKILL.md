---
name: alphagsm-boot-activation
description: "Use when enabling or disabling AlphaGSM server startup on boot using the existing user scheduler."
---

# Configure boot activation

Follow the [installation and request policy](../alphagsm-server-requirements/references/approval-gates.md). AlphaGSM-managed code, helpers, repository image builds and supported prerequisites proceed within the requested task without extra approval. Ask only for new software outside that managed scope, and clarify an unspecified action/target on an existing server.

Inputs: selected tag/owner, enable/disable intent, and whether to start/stop now. Read [everyday commands](../../docs/commands.md). On Unix this is a user crontab workflow; verify the selected account's crontab and executable/config paths without changing unrelated jobs. Standalone Windows does not install a boot scheduler through this command.

```bash
alphagsm mymc activate --delay
alphagsm mymc deactivate --delay
```

`activate --delay` adds boot startup without starting now. Plain activate also starts. `deactivate --delay` removes boot startup without stopping now. Plain deactivate also stops. Select the variant that matches the user's requested current state, not merely their future boot intent.

The current generated job does not persist ALPHAGSM_CONFIG_LOCATION, and executable paths with spaces are not robustly quoted/recognized. For these installations, report the scheduler limitation rather than claiming next-boot readiness or silently prefixing an env command that activate/deactivate cannot recognize. A separate custom scheduler change needs explicit scope. Check that the resulting reboot job points at the correct executable/tag and usable environment. Capture only relevant job lines; do not expose unrelated account configuration. Verify there is no duplicate managed entry after repeated activation. A missing scheduler or permission is a concrete host prerequisite, not a reason to install a different background agent implicitly.

If the operation changes current service state, [verify health/shutdown](../alphagsm-health-check/SKILL.md). Finish with both scheduler state and server state. Example: “Start my server on reboot, but leave it stopped today” uses activate with delay and proves it remained stopped.
