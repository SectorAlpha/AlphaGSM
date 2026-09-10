# Silica

This guide covers the `silicaserver` module in AlphaGSM.

`silicaserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

The current native configuration and query corrections await replacement CI;
the tracker records historical validation.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysilicase create silicaserver
```

Run setup:

```bash
alphagsm mysilicase setup
```

Start it:

```bash
alphagsm mysilicase start
```

Check it:

```bash
alphagsm mysilicase status
```

Stop it:

```bash
alphagsm mysilicase stop
```

## Setup Details

Setup configures:

- the game port (default UDP 26900) and Steam query port (default UDP 26901)
- the install directory
- SteamCMD downloads the server files
- AlphaGSM writes `ServerSettings.xml` in the installation's
  `.alphagsm-home/Silica` directory. Process and Docker runtimes use that same
  persistent configuration, including managed server name and player limit.

## Useful Commands

```bash
alphagsm mysilicase update
alphagsm mysilicase backup
```

## Notes

- Module name: `silicaserver`
- Default port: 26900
- Existing XML game-mode, map, and administration settings are preserved. If no
  instance configuration exists, AlphaGSM copies an existing `~/Silica/ServerSettings.xml`
  into the instance without changing the original.
- `query` and `info` require Steam A2S on `queryport`. Native XML configuration
  follows the [publisher's server setup guidance](https://silicagame.com/news/update_0818)
  and the [server configuration template](https://github.com/Casraw/silica-docker-server/blob/51ddf5bd2c99ca98915a1b8247eacb370806e35a/ServerSettings.template.xml).

<!-- alphagsm-server-variables:start -->

## Server variables

After `create silicaserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `servername` | hostname, name | string | Name advertised by the Silica server. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `Silica.x86_64`
- **Location**: `<install_dir>/Silica.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2738040`

### Server Configuration

- **Config file**: `.alphagsm-home/Silica/ServerSettings.xml`
- **Max players**: `64`
- **Template**: See [server-templates/silicaserver/](../server-templates/silicaserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
