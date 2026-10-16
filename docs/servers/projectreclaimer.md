# Project Reclaimer

Status: **pending real BYO validation**. The importer, configuration, native RCON
protocol and runtime contracts have automated tests. Real MCC startup, player
connectivity and shutdown have not been validated for this module; it is not yet
recorded as `PASSED` or `ENABLED (BYO)`.

Project Reclaimer hosts Halo 3 multiplayer using an owned Steam installation of
Halo: The Master Chief Collection, including Halo 3 Campaign and Multiplayer.
AlphaGSM downloads the public Reclaimer dedicated executable, pinned to 0.9.18
and checked against its published SHA-256. No MCC game files are downloaded.

This initial module manages one fixed map/game per AlphaGSM server, using
Guardian and Slayer by default. Existing playlist, variant or campaign selection
is rejected before the configuration is rewritten. Standard title-to-file map
translation and management of those advanced selections are not implemented.
`set map` accepts Guardian or an installed map file stem that Reclaimer accepts.

## Windows

Install the Visual C++ 2015–2022 runtime, then run in PowerShell:

```powershell
.\alphagsm.exe halo create projectreclaimer
.\alphagsm.exe halo setup -n 49176 "C:\Servers\Reclaimer" --assets "D:\SteamLibrary\steamapps\common\Halo The Master Chief Collection"
.\alphagsm.exe halo assets check
.\alphagsm.exe halo start
.\alphagsm.exe halo query
.\alphagsm.exe halo info --json
.\alphagsm.exe halo stop
```

The Windows process launches the downloaded executable directly. The portable
asset commands are also covered by Windows CI; a Windows test pass on this branch
must be confirmed by that workflow.

## Linux with an AlphaGSM-built image

Build from the current checkout:

```bash
docker build -t alphagsm-wine-proton-runtime:local -f docker/wine-proton/Dockerfile .
```

Set `backend = docker` in the `[runtime]` section of your AlphaGSM configuration,
following [Docker-backed servers](../docker-runtime-host.md), then:

```bash
./alphagsm halo create projectreclaimer
./alphagsm halo set image alphagsm-wine-proton-runtime:local
./alphagsm halo setup -n 49176 /srv/reclaimer --assets /srv/uploads/reclaimer-assets.zip
./alphagsm halo assets check
./alphagsm halo start
./alphagsm halo query
./alphagsm halo info --json
./alphagsm halo stop
```

See [owned asset imports and exports](../owned-assets.md) to create that ZIP on
Windows. Prepared upstream server folders containing `game/halo3/` also work.
Use x86-64 Linux. This module uses host networking so its RCON listener remains
local; run AlphaGSM on the host or in a manager container sharing the host network.
Bridge-networked managers are not supported by this initial RCON path.

The existing repository Wine/Proton image supplies Wine and Visual C++ runtimes.
The module mounts `<install_dir>/game` read-only. Config, content and Wine state
remain writable in the server directory. Docker is configured to send SIGINT
and allow 30 seconds for shutdown. Real graceful shutdown remains unverified.
The Linux process path uses the shared Wine/Proton wrapper when Docker is not selected.

## Settings and content

```bash
./alphagsm halo set servername "Friends Halo"
./alphagsm halo set maxplayers 32
./alphagsm halo rcon "status"
./alphagsm halo message "Welcome everyone"
```

`port` is the UDP game port (default 49176). `rconport` is a separate TCP port
(default the initial game port plus one), bound to `127.0.0.1`. Both participate
in AlphaGSM port claims. The optional local master is disabled. Set a game port
explicitly if needed before running setup; external master advertising is handled
by Reclaimer. Do not expose the RCON port publicly.

AlphaGSM generates an RCON password and stores it using its normal secret
datastore support. `dedicated.toml` contains the required runtime copy and is
written with owner-only permissions on POSIX; configure the server folder's ACL
appropriately on Windows. Client and server Reclaimer versions must match.

### Developer notes

- Public module: `gamemodules.projectreclaimer`, implementation in `main.py`.
- Executable: `<install_dir>/project-reclaimer.exe`, arguments `dedicated`.
- Configuration: `<install_dir>/dedicated.toml`; managed keys sync on setup,
  prestart, update and `set`. Other configuration lines are preserved.
- Asset recipe: Halo 3 DLLs and map files under `game/halo3/`. Required base
  files include `halo3.dll`, `shared.map`, `campaign.map`, `040_voi.map` and
  the configured map. Extra maps are included when present in the source.
- Content paths: `content/Maps`, `content/Game Modes`, `content/Mods`, and `playlists`.
  The importer intentionally excludes these and source configuration files.
- Query/info protocol: authenticated `reclaimer_rcon` WebSocket status; only
  public name/map/population/mode/phase/version fields are returned.
- Config reference: [dedicated.toml](../server-templates/projectreclaimer/dedicated.toml).

## Deferred lifecycle validation

Supply legitimate owned files and run each runtime separately:

```bash
ALPHAGSM_RECLAIMER_ASSETS=/path/to/owned/files \
  PYTHON_BIN=python3 make smoke-test SMOKE_TEST=run_projectreclaimer.sh

ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RECLAIMER_ASSETS=/path/to/owned/files \
  ALPHAGSM_TEST_RUNTIME_BACKEND=docker \
  ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON=alphagsm-wine-proton-runtime:local \
  PYTHONPATH=.:src python3 -m pytest tests/integration_tests/test_projectreclaimer.py -v
```

Portable entry point: `python tests/smoke_tests/reclaimer_lifecycle.py --assets PATH
--runtime process` works on Windows and Linux. Missing source files skip the
smoke with exit 77; bad sources, readiness timeouts and shutdown failures fail.
After real process and Docker passes, update the support tracker and guide status.

Upstream: [hosting](https://projectreclaimer.dev/host),
[release 0.9.18](https://github.com/ProjectReclaimer/project-reclaimer-releases/releases/tag/v0.9.18),
[RCON protocol](https://github.com/ProjectReclaimer/project-reclaimer-releases/releases/download/v0.9.18/RCON.md).
