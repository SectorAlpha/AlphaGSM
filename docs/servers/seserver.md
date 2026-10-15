# Space Engineers

This guide covers the `seserver` module in AlphaGSM.

`seserver` retains its prior `PASSED` support classification. GitHub
validation uses the supported Docker `wine-proton` runtime. AlphaGSM passes
`Z:\srv\server` as Wine's data directory so the dedicated server reads and
writes inside the mounted installation.

Keen's [dedicated-server guide](https://www.spaceengineersgame.com/dedicated-servers/)
defines `-path` as the directory used to load configuration and store server
files. In Docker, this directory maps to the AlphaGSM installation on the host,
so configuration, saves, and logs remain accessible there.

## Workshop validation checkpoint

Native Workshop process support is under validation as of 15 October 2026. Anonymous
downloads succeeded for consumer app `244850`, including the public
[Modular Encounters Systems server framework](https://steamcommunity.com/sharedfiles/filedetails/?id=1521905890)
(31,485,392 bytes). Focused Docker integration and smoke subsequently passed
the complete modded lifecycle; process completion is still pending.

The adapter manages Steam mod references in the configured world's
`Sandbox.sbc` and `Sandbox_config.sbc`, preserving operator entries. A missing
default world is seeded from the dedicated server's own Empty World template;
existing saves are preserved. Native world paths must stay inside the
installation.

Process CI on 14 October reached the engine but stopped with a missing
Visual C++ 2015–2019 x64 runtime message. Its fresh Proton prefix had bypassed
the prepared Wine prefix in the runtime image. Process startup now prefers
Wine and seeds only a fresh private prefix from `/opt/wine` when available;
existing operator prefixes are preserved. Linux uses the vendor-supported
`-noconsole` option. The correction still needs a fresh CI lifecycle pass.
Existing Proton compatibility directories keep Proton when available; Wine
fallback opens their existing inner `pfx` directory.

Focused Docker integration and Workshop smoke passed the strict execution
checks on 14 October 2026. Process CI progressed past the runtime check but
exited during Steam initialization after binding its port. Process launch now
uses `xvfb-run` and the same X11/SDL drivers as the passing Docker runtime;
CI run `38655040006` still exited before `Game ready` after that correction.
CI run `38702811625` confirmed the passing Docker runtime uses the same
Windows 7 and Mono 6.13.0 identity. Both failing process cases reported a
missing Wine `LocalAppDataLow` folder followed by a handled access violation;
no native crash dump was produced. The prepared prefix retained the image
builder's `.update-timestamp`, which can cause Wine to skip shell-folder setup
when the copy runs under another account. Fresh template copies now discard
that copied marker so Wine initializes the receiving user's profile normally;
the template and existing operator prefixes retain their markers. This
correction still needs a process CI lifecycle pass. See Wine's
[prefix update logic](https://github.com/wine-mirror/wine/blob/wine-9.0/programs/wineboot/wineboot.c#L1457)
and [shell-folder creation](https://github.com/wine-mirror/wine/blob/wine-9.0/dlls/shell32/shellpath.c#L2901).

Workshop integration and opt-in smoke require both `Game ready` and the MES
script's own `MES Spawner / Startup: Active Debug ...` initialization message.
An item ID, mod name, download, or world configuration alone does not prove
engine execution. Process Workshop completion remains unverified.
The prior baseline classification above does not establish Workshop support.

## Requirements

- Docker
- Python packages from `requirements.txt`

For a Linux process server, install Wine, `xvfb-run`, and the upstream Visual C++ runtime
prerequisites in its private prefix. The AlphaGSM runtime image already
prepares these prerequisites in `/opt/wine`; another prepared template may be
selected with `ALPHAGSM_WINEPREFIX_TEMPLATE`. Existing prefixes are not changed
by template seeding. Integration and smoke honor
`ALPHAGSM_TEST_RUNTIME_BACKEND=process|docker`; public Workshop validation
additionally requires `ALPHAGSM_RUN_WORKSHOP=1`.

## Quick Start

Create the server:

```bash
alphagsm myseserver create seserver
```

Run setup:

```bash
alphagsm myseserver setup
```

Start it:

```bash
alphagsm myseserver start
```

Check it:

```bash
alphagsm myseserver status
```

Stop it:

```bash
alphagsm myseserver stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm myseserver update
alphagsm myseserver backup
```

## Notes

- Module name: `seserver`
- Default port: 27016
- Current validation status: PASSED 2026-05-31. Fresh focused integration now
  proves the old missing-binary disable note was stale in a narrower way:
  anonymous SteamCMD setup for app `298740` installs the real Windows
  dedicated payload, AlphaGSM launches the server through the shared Docker
  `wine-proton` runtime, and `query`, `info`, and `info --json` all succeed on
  the current generic `udp` health surface at the managed main game port.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create seserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `DedicatedServer64/SpaceEngineersDedicated.exe`
- **Location**: `<install_dir>/DedicatedServer64/SpaceEngineersDedicated.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `298740`

The validated Linux support path runs through AlphaGSM's Docker-backed
`wine-proton` runtime image rather than a host `screen` session. The current
checked-in integration and smoke coverage launch the Windows dedicated server
from its required `DedicatedServer64` working directory with `-noconsole` on Linux,
`-path`, and `-port`, then validate the live contract on the managed main
game port: `query`, `info`, and `info --json` all succeed as generic `udp`.

### Server Configuration

- **Config files**: generated by the dedicated server under the managed data path
- **Template**: see the dedicated server's generated config after first launch

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: Native world activation is implemented; live lifecycle validation is pending.
