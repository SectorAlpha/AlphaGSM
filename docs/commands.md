# Everyday Commands

This is the full AlphaGSM command surface operators actually get. The first
table is the shared lifecycle. The rest is day-two work: console, backups,
boot, and discovery.

Every server also has `alphagsm <name> --help` for the exact flags of that
game.

## Lifecycle

| Command | What it does |
| --- | --- |
| `alphagsm list` | Print this user's servers, one per line |
| `alphagsm <name> create <module>` | Register a new server |
| `alphagsm <name> setup` | Download files and write config |
| `alphagsm <name> start` | Launch the dedicated server |
| `alphagsm <name> status` | Running or not; `-v` for more detail |
| `alphagsm <name> query` | Network health check |
| `alphagsm <name> info` | Player/map/version style details; `--json` for scripts |
| `alphagsm <name> stop` | Graceful shutdown |
| `alphagsm <name> restart` | Stop, then start |
| `alphagsm <name> kill` | Immediate force-kill if stop is stuck |

`setup -n` fails instead of prompting. Pass port and directory when you already
know them: `alphagsm mymc setup -n 25565 "$HOME/minecraft-server"`.

## Console and logs

| Command | What it does |
| --- | --- |
| `alphagsm <name> message "hello"` | In-game broadcast when the game supports it |
| `alphagsm <name> send "sv_cheats 0"` | One line to the **server console**, not player chat |
| `alphagsm <name> connect` | Attach to the live console (screen/tmux/Docker). Subprocess `connect` only follows logs |
| `alphagsm <name> logs` | Last 50 log lines; `-n 200` for more |

## Settings

```bash
alphagsm mytf2 set --list
alphagsm mytf2 set gamemap --describe
alphagsm mytf2 set gamemap --values
alphagsm mytf2 set gamemap cp_dustbowl
alphagsm mytf2 set rconpassword secret
```

`--list` shows schema-backed keys. `--describe` / `--values` inspect one key.
Passwords and other secret keys go into a mode-0600 secrets file, not the
normal datastore.

`alphagsm <name> dump` prints the raw datastore. That is a debug tool, not
something you need for daily use.

## Backups and worlds

```bash
alphagsm mymc backup
alphagsm mymc restore          # list available backups
alphagsm mymc restore 0        # restore by index
alphagsm mymc restore backup-filename.tar.gz
```

Restore stops the server first. `reset-world` / `wipe` delete **world data
only**, with a confirmation prompt (`-Y` skips it). See
[World creation and reset](world-management.md).

## Start on boot

```bash
alphagsm mymc activate          # crontab + start now
alphagsm mymc activate --delay  # crontab only
alphagsm mymc deactivate
```

`activate` needs a working user crontab on Unix. Standalone Windows binaries
do not install a boot scheduler.

## Runtime check

```bash
alphagsm mymc doctor
alphagsm mymc doctor --json
```

Use this before `start` when you care which backend, image, or container
AlphaGSM will use.

## Mods, maps, and updates

- Mods: [Installing Mods](installing-mods.md)
- Game files and the AlphaGSM binary: [Updating Servers And AlphaGSM](updating.md)

TF2 also has a map command with the same add-then-apply shape:

```bash
alphagsm mytf2 map add curated cp_granary_pro_rc8
alphagsm mytf2 map apply
alphagsm mytf2 map list
```

## Support labels

[Game Server Support](game-server-support.md) uses three operator-facing
states besides a plain pass:

- **PASSED** — AlphaGSM can provision and run it on the documented Linux path
- **ENABLED (AUTH)** — you still need a Steam login, license key, token, or similar
- **ENABLED (BYO)** — you still supply owned files, an export, or a download URL

`DISABLED` means AlphaGSM will refuse `create` for that module.

## More than one server

```bash
alphagsm list
alphagsm '*' status
```

`*` means every server for the current user. `username/server` runs as that
user through `sudo` when permitted.
