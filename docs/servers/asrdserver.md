# Alien Swarm: Reactive Drop

The `asrdserver` module installs the anonymous Windows dedicated-server files and
runs them through Wine on Linux. The baseline process lifecycle passed in CI on
2026-10-14. Docker validation is pending a rerun of the native console fix;
Workshop load validation remains opt-in and unverified.

## Requirements

- Linux process runtime: `screen`, Wine with 32-bit support, and SteamCMD libraries.
- Docker runtime: the shared `wine-proton` image and a working Docker endpoint;
  host Wine and screen are not prerequisites for this runtime.
- Enough space for the game depot, a private Wine prefix and Workshop content.

The ASRD Docker spec keeps stdin open with a terminal so Wine can create the
native Win32 console input handle. Pipe-backed input previously caused an early
`CTextConsoleWin32::GetLine` exit. The module uses Docker stop rather than the
console FIFO path; its process launcher is unchanged. This follows
[Wine's terminal-to-console initialization](https://github.com/wine-mirror/wine/blob/wine-9.0/dlls/ntdll/unix/env.c#L1298).

```bash
alphagsm myasrd create asrdserver
alphagsm myasrd setup
alphagsm myasrd start
alphagsm myasrd status
alphagsm myasrd query
alphagsm myasrd info
alphagsm myasrd info --json
alphagsm myasrd stop
```

Setup anonymously installs AppIDs `1007` and `563560` into one directory, following
[the upstream dedicated-server FAQ](https://github.com/ReactiveDrop/developer.reactivedrop.com/blob/gh-pages/faq.md).
The launcher is `srcds_console.exe -console -condebug -game reactivedrop`.
The private Wine prefix defaults to `<install_dir>/.wine`; engine config lives in
`reactivedrop/cfg/server.cfg`. Empty-server shutdown and hibernation are disabled
so real A2S query and info remain available. No GSLT, Steam account or API key is
supplied.

Set `ALPHAGSM_WORK_DIR` to a large disk for integration and smoke work. Choose an
install directory on that disk during setup too. Game UDP/TCP, client UDP and
SourceTV UDP ports are managed by AlphaGSM. Common settings include `port`,
`clientport`, `sourcetvport`, `map`, `servername`, `maxplayers`, `serverpassword`
and `rconpassword`.

The smoke runner honors `ALPHAGSM_TEST_RUNTIME_BACKEND=process` or `docker`.
An explicit `auto` uses this module's Docker runtime. Without an explicit backend,
CI or a supplied `ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON` selects Docker; local
runs otherwise use process. The supplied image is written into the smoke config
so CI uses its branch image. Integration setup preserves an explicit
`ALPHAGSM_ASRDSERVER_STEAMCMD_PATH` without adding a duplicate config section when
`ALPHAGSM_WORK_DIR` already provides one.

## Native Workshop content

```bash
alphagsm myasrd mod add workshop 848331447
alphagsm myasrd mod add workshop-collection YOUR_COLLECTION_ID
alphagsm myasrd mod apply
alphagsm myasrd start
```

Official Steam Community URLs work in place of IDs. AlphaGSM validates consumer
AppID `563560` and expands collections, then writes an owned block of native
`rd_enable_workshop_item` commands into `reactivedrop/cfg/workshop.cfg`. The engine
executes that file and downloads/mounts the actual addon. Select multiplayer
campaigns, maps or server-compatible challenges; cosmetic/client-only uploads do
not establish a usable dedicated-server workload.

Apply while stopped. Existing operator commands and comments remain outside the
managed block. External changes to that block and unsafe symlink paths are
rejected. `mod cleanup` removes only its unchanged block and deletes a config it
created only when empty; engine-managed caches remain. It preserves the selected
map setting, so select an installed ordinary map before restarting if needed.

The public [Nest fixture](https://steamcommunity.com/sharedfiles/filedetails/?id=848331447)
is a small multiplayer campaign. Its opt-in test requires the running engine's
`rd_dump_workshop_mapping_server maps/` output to attribute an actual map to this
item, executes that map, and checks real A2S before shutdown and owned cleanup.
The probe uses a generated local RCON password, separate from provider credentials.
Remote-client content delivery has not been verified.

```bash
ALPHAGSM_WORK_DIR=/path/on/large/disk \
ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 \
ALPHAGSM_RUN_ASRDSERVER_WORKSHOP=1 \
python3 -m pytest tests/integration_tests/test_asrdserver.py -k workshop

ALPHAGSM_WORK_DIR=/path/on/large/disk ASRD_WORKSHOP_ITEM=848331447 \
make smoke-test SMOKE_TEST=run_asrdserver.sh
```

Use `ALPHAGSM_ASRDSERVER_WORKSHOP_COLLECTION` to exercise a collection,
`ALPHAGSM_ASRDSERVER_WORKSHOP_LOAD_ITEM` to select its fixture item and
`ALPHAGSM_ASRDSERVER_WORKSHOP_MAP` to select a specific map. Smoke uses matching
`ASRD_WORKSHOP_*` variables.
