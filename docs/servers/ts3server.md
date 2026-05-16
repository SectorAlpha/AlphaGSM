# TeamSpeak 3

This guide covers the `ts3server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myts3serve create ts3server
```

Run setup:

```bash
alphagsm myts3serve setup
```

Start it:

```bash
alphagsm myts3serve start
```

Check it:

```bash
alphagsm myts3serve status
```

Stop it:

```bash
alphagsm myts3serve stop
```

## Setup Details

Setup configures:

- the game port (default 10011)
- the install directory

## Useful Commands

```bash
alphagsm myts3serve update
alphagsm myts3serve backup
```

## Notes

- Module name: `ts3server`
- Default port: 10011

## Developer Notes

### Run File

- **Executable**: `ts3server`
- **Location**: `<install_dir>/ts3server`
- **Engine**: Custom

Smoke and integration validation wait for the TeamSpeak startup log to report
`ServerQuery created`, then require `alphagsm info --json` to report protocol
`ts3`.

### Server Configuration

- **Config files**: `ts3server.ini`
- **Template**: See [server-templates/ts3server/](../server-templates/ts3server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
