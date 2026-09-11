# Arma 3 Desolation Redux

This guide covers the `arma3desolationreduxserver` module in AlphaGSM.

## Status

`arma3desolationreduxserver` is currently `ENABLED (AUTH)`.

Before `setup`, authenticate Steam or SteamCMD with an account entitled to
Arma 3 dedicated server app `233780`.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarma3des create arma3desolationreduxserver
```

Run setup:

```bash
alphagsm myarma3des setup
```

Start it:

```bash
alphagsm myarma3des start
```

Check it:

```bash
alphagsm myarma3des status
```

Stop it:

```bash
alphagsm myarma3des stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarma3des update
alphagsm myarma3des backup
```

## Notes

- Module name: `arma3desolationreduxserver`
- Default port: 2302

<!-- alphagsm-server-variables:start -->

## Server variables

After `create arma3desolationreduxserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `servername` | hostname, name | string | The public hostname written to server.cfg. Example: `AlphaGSM Server`. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `arma3server_x64`
- **Location**: `<install_dir>/arma3server_x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `233780`

### Server Configuration

- **Config file**: `server.cfg`
- **Template**: See [server-templates/arma3desolationreduxserver/](../server-templates/arma3desolationreduxserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
