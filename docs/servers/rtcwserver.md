# Return to Castle Wolfenstein

This guide covers the `rtcwserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myrtcwserv create rtcwserver
```

Run setup:

```bash
alphagsm myrtcwserv setup
```

Start it:

```bash
alphagsm myrtcwserv start
```

Check it:

```bash
alphagsm myrtcwserv status
```

Stop it:

```bash
alphagsm myrtcwserv stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myrtcwserv update
alphagsm myrtcwserv backup
```

## Notes

- Module name: `rtcwserver`
- Default port: 27960
