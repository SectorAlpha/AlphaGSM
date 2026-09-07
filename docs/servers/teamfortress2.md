# Team Fortress 2-specific

This guide covers the `teamfortress2` module in AlphaGSM.

The checked-in support tracker currently marks the canonical Team Fortress 2
surface as `PASSED` on the documented Ubuntu 24.04 Linux baseline under the
`tf2` module id. `teamfortress2` is the package-backed canonical import
surface behind that validated TF2 server path.

## Requirements

The current AlphaGSM process integration requires Linux because it uses
`srcds_run` and Linux Steam client libraries. Setup rejects incompatible hosts
before downloading. Docker requires a Linux-container daemon, including when
Docker runs on a Windows desktop. Installation still uses the Linux SteamCMD
client on the manager host; run AlphaGSM itself in Linux or in the manager
container for this setup path.

- Optional `screen` or `tmux`; the subprocess backend is also available
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- For source installations, Python packages from `requirements-runtime.txt`

## Quick Start

Create the server:

```bash
alphagsm myteamfort create teamfortress2
```

Run setup:

```bash
alphagsm myteamfort setup
```

Start it:

```bash
alphagsm myteamfort start
```

Check it:

```bash
alphagsm myteamfort status
```

Stop it:

```bash
alphagsm myteamfort stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

The native TF2 config lives at `tf/cfg/server.cfg`. AlphaGSM keeps the
following values in sync through `set`:

- `set gamemap` aliases `map`, `startmap`, and `level`
- `set servername` updates the `hostname` entry in `server.cfg`
- `set rconpassword` updates `rcon_password`
- `set serverpassword` updates `sv_password`

Examples:

```bash
alphagsm myteamfort set gamemap --describe
alphagsm myteamfort set gamemap cp_dustbowl
alphagsm myteamfort set rconpassword secret
```

## Useful Commands

```bash
alphagsm myteamfort update
alphagsm myteamfort backup
```

## Curated Mod Support

AlphaGSM now has a TF2-first curated server-side mod foundation for
package-backed installs that land inside the normal TF2 server tree.

Use the curated workflow to declare the desired mod set and then reconcile it:

```bash
alphagsm myteamfort mod add curated sourcemod
alphagsm myteamfort mod apply
```

Notes:

- `sourcemod` is the main curated example and can be pinned to an explicit channel when the registry exposes one, for example `alphagsm myteamfort mod add curated sourcemod 1.12`.
- The checked-in TF2 curated registry also carries package-backed metadata for `metamod`, so the same workflow applies there when you want MetaMod first.
- `mod apply` is the point where AlphaGSM reconciles the desired curated entries into the TF2 install and keeps ownership tracking on AlphaGSM-managed files.

## Workshop Status

Workshop support is still experimental.

- You can record a desired workshop item with `alphagsm myteamfort mod add workshop <numeric_id>`.
- Workshop apply/download is not yet verified for TF2, so treat workshop entries as desired-state groundwork rather than a supported install path today.
- Expect the curated path to be the supported operator flow for now.

## Notes

- Module name: `teamfortress2`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `232250`

### Server Configuration

- **Config files**: `server.cfg`
- **Template**: See [server-templates/teamfortress2/](../server-templates/teamfortress2/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Curated mod directories**: `tf/addons` and `tf/cfg`
- **Curated mod examples**: `sourcemod`, `metamod`
- **Workshop support**: Experimental desired-state support only; apply/download is not yet verified
