# Everyday Commands

This is the full AlphaGSM command surface operators actually get. The first
table is the shared lifecycle. The rest is day-two work: console, backups,
boot, and discovery.

Every server also has `alphagsm <name> --help` for the exact flags of that
game.

## Lifecycle

| Command | What it does |
| --- | --- |
| `alphagsm '*' list` | Print this user's servers, one per line |
| `alphagsm <name> create <module>` | Register a new server |
| `alphagsm <name> setup` | Download files and write config |
| `alphagsm <name> start` | Launch the dedicated server |
| `alphagsm <name> status` | Running or not; `-v` for more detail |
| `alphagsm <name> query` | Network health check |
| `alphagsm <name> info` | Player/map/version style details; `--json` for scripts |
| `alphagsm <name> stop` | Graceful shutdown |
| `alphagsm <name> restart` | Stop, then start |
| `alphagsm <name> kill` | Immediate force-kill if stop is stuck |

`setup -n` disables prompts; supply the required game values as well as port
and directory. For fresh Minecraft, after accepting the game's EULA, use
`alphagsm mymc setup -n -l 25565 "$HOME/minecraft-server"`.
Without that EULA choice, setup can finish while the game still refuses to start.

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
alphagsm mymc restore backup-filename.zip
```

Backups use ZIP archives. Check the module's backup support: TF2 currently
advertises the shared command but has no backup hook.
Restore stops the server first. `reset-world` / `wipe` default to `--mode soft`
and delete world data, with a confirmation prompt (`-Y` skips it).
`--mode hard` reinstalls the server files and puts declared configuration back.
`set memory 2g` and `set cpus 1.5` cap a Docker game container. A Java server
with no `-Xmx` then uses 75 percent of that memory limit. See
[World creation and reset](world-management.md).

To copy a server onto another machine, back it up, copy the install tree,
`create` on the new host, then restore or re-run `setup`.

## Start on boot

```bash
alphagsm mymc activate          # crontab + start now
alphagsm mymc activate --delay  # crontab only
alphagsm mymc deactivate
```

`activate` needs a working user crontab on Unix. Standalone Windows binaries
do not install a boot scheduler.
The current generated job does not preserve a custom `ALPHAGSM_CONFIG_LOCATION`
and does not robustly handle executable paths containing spaces. Check that
the job can find your intended installation before relying on boot startup.

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
- **ENABLED (BYO)** — you still supply owned files, staged game assets, or a download URL

`DISABLED` means AlphaGSM will refuse `create` for that module.

## More than one server

```bash
alphagsm '*' list
alphagsm '*' status
```

`*` means every server for the current user. `username/server` runs as that
user through `sudo` when permitted.

## SteamCMD session profiles

SteamCMD session profiles support explicit owned-file setup for declared BYO
Steam sources. See [SteamCMD session profiles](steamcmd-auth.md) for their scope;
legacy AUTH-gated modules are not automatically migrated.


## Game-specific BYO files

```bash
alphagsm myserver assets requirements
alphagsm myserver assets check --json
alphagsm myserver assets import /path/to/owned-game
alphagsm steam-auth login owned your_steam_username
alphagsm myserver setup --auth-profile owned
alphagsm myserver setup --steam-dir /path/to/SteamLibrary/steamapps
alphagsm myserver assets fetch steam-owned --auth-profile owned
alphagsm steam-auth status owned
alphagsm steam-auth logout owned
```

Only recipes that declare managed import support can import or fetch files.
The server must be stopped for those actions. `requirements` explains the
game-specific source, files and destinations without login. `check` validates
files, not server readiness. See [BYO files](byo-files.md) and
[private SteamCMD sessions](steamcmd-auth.md).

`setup --auth-profile NAME` remembers the profile name per server and downloads
missing declared files. `setup --steam-dir PATH` locates the installed source
app by AppID and imports its allowlisted files. It overrides remembered auth
for that run, as does `--assets PATH`; explicit source options are mutually
exclusive. Clear remembered auth with `set steam_auth_profile DELETE`.

The same commands apply to a host binary and to a Python library call. When
game servers use Docker, the login still runs in that AlphaGSM process and the
private profile is not mounted into the game container. Inside the manager
container, run `./alphagsm-docker steam-auth login owned your_steam_username`
from a terminal. A non-terminal login is rejected. See
[SteamCMD session profiles](steamcmd-auth.md). Live auth and BYO tests run
locally with `./run_local_tests.sh`.
