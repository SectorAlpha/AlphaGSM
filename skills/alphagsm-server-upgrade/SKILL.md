---
name: alphagsm-server-upgrade
description: "Use when upgrading game server files or the AlphaGSM manager and verifying recovery and health."
---

# Upgrade a server or manager

Read [updating](../../docs/updating.md), the selected module's help and current versions/state. Distinguish game files from AlphaGSM itself. Back up mutable data and retain a recoverable prior install/version when rollback is required; a save archive alone may not restore an older binary.

For a supported SteamCMD game:

```bash
alphagsm mytf2 --help
alphagsm mytf2 update -v
```

Verify flags and backup capability in the actual module, not just shared help. TF2 currently lacks a backup hook; retain a scoped staged copy before replacing its files when recovery is required. Standard SteamCMD update stops the server and leaves it stopped; `-r` requests restart. Preserve the requested service state deliberately. URL-backed games use their actual setup options, not an invented universal update command. Minecraft Vanilla takes `setup -n -l PORT DIR --version VERSION` or `--url URL`; it does not accept version/url through set. Inspect changes to saves/config/mod compatibility before launch.

For the manager:

```bash
alphagsm self-update --check
alphagsm self-update
```

Only execute replacement when requested. A git self-update requires a clean eligible tracking branch and refuses developer branches/divergence; do not discard work to make it succeed. Standalone replacement uses verified release assets. On Windows, inspect the deferred result file before claiming replacement succeeded.

Run doctor and [health checks](../alphagsm-health-check/SKILL.md) after restarting affected services as intended. Bound retries to an identified correction. If an update fails, preserve diagnostics and recovery options rather than retrying downloads/restarts indefinitely. Report previous/new versions, compatibility findings and final state per tag.
