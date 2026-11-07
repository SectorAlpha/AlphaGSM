---
name: alphagsm-server-provision
description: "Use when creating, setting up or starting a named AlphaGSM game server unattended."
---

# Provision a server

Inputs: selected host/config, owner/tag, supported module, install path, ports, required game values/assets, and final running state. Read [execution context](../alphagsm-agent-operations/references/execution-context.md), the matching guide, and the canonical [Minecraft](../../tests/smoke_tests/run_minecraft_vanilla.sh) or [TF2](../../tests/smoke_tests/run_tf2.sh) smoke pattern.

First inspect installation state using [server-requirements](../alphagsm-server-requirements/SKILL.md) and its [request policy](../alphagsm-server-requirements/references/approval-gates.md). For a vague run request with no installation, ask to install that game. If it already exists, clarify the action unless specified. Explicit actions and approved installs proceed through AlphaGSM, including managed SteamCMD/helper steps and repository image pulls/builds. There is no separate Docker first-use gate. Ask only for additional new external software outside that scope.

1. List servers and inspect existing state. Reuse a matching healthy tag; stop if the tag belongs to a different game or setup would overwrite unreviewed assets.
2. Check support prerequisites and module/platform support. Create only a missing tag.
3. Inspect `myserver --help`, `set --list`, and `help setup`; provide known required values with `setup -n` so missing inputs fail instead of prompting.
4. Apply game-specific prerequisites/configuration through supported settings. For Terraria/TShock/Necesse, use explicit `start --autocreate` only when creating the configured missing world is intended; never answer an unknown console prompt blindly.
5. Run doctor, start through AlphaGSM, and [check real readiness](../alphagsm-health-check/SKILL.md) with a deadline. Diagnose one failed attempt before retrying; do not repeatedly overwrite or restart.

Minecraft example after an explicit/approved installation request, a supported URL, install path and operator EULA acceptance have been established (`-l` records that choice). Use the selected AlphaGSM executable, or forward these same tag commands through the selected manager wrapper:

```bash
alphagsm mymc create minecraft.vanilla
alphagsm mymc setup -n -l 25565 /srv/alphagsm/mymc -u "$SERVER_URL"
alphagsm mymc doctor --json
alphagsm mymc start
alphagsm mymc query
alphagsm mymc info --json
```

This is the fresh-tag path, not an idempotent script to rerun blindly. Reachability is checked after protocol readiness, not immediately assumed after start. Finish running when requested; temporary validation installations must stop and prove listener/process closure. Retain the specific blocker if setup cannot complete.
