# Don't Starve Together

This guide covers the `dstserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydstserve create dstserver
```

Run setup:

```bash
alphagsm mydstserve setup
```

Start it:

```bash
alphagsm mydstserve start
```

Check it:

```bash
alphagsm mydstserve status
```

Stop it:

```bash
alphagsm mydstserve stop
```

## Setup Details

Setup configures:

- the game port (default 10999)
- the install directory
- SteamCMD downloads the server files

Don't Starve Together is currently a bring-your-own-config lane in AlphaGSM.
The anonymous server payload installs, but startup still exits immediately
unless you provide both:

- a real `cluster_token.txt`
- a real cluster config directory for the world you want to run

With the module defaults, AlphaGSM starts DST with:

- `-persistent_storage_root <install_dir>`
- `-conf_dir DoNotStarveTogether`
- `-cluster <server-name>`
- `-shard Master`

That means the expected default layout is:

```text
<install_dir>/DoNotStarveTogether/<server-name>/
├── cluster_token.txt
├── cluster.ini
└── Master/
    └── server.ini
```

If you change `cluster`, `shard`, or `confdir` with `alphagsm set`, place the
files under the matching adjusted path before retrying `start`.

Example:

```bash
alphagsm mydstserve create dstserver
alphagsm mydstserve setup
mkdir -p "<install_dir>/DoNotStarveTogether/mydstserve/Master"
# Copy your real Klei token and cluster config into that directory tree
alphagsm mydstserve start
```

## Useful Commands

```bash
alphagsm mydstserve update
alphagsm mydstserve backup
```

## Notes

- Module name: `dstserver`
- Default port: 10999

## Developer Notes

### Run File

- **Executable**: `bin64/dontstarve_dedicated_server_nullrenderer_x64`
- **Location**: `<install_dir>/bin64/dontstarve_dedicated_server_nullrenderer_x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `343050`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/dstserver/](../server-templates/dstserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
