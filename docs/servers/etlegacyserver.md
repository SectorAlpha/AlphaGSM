# ET: Legacy

This guide covers the `etlegacyserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myetlegacy create etlegacyserver
```

Run setup:

```bash
alphagsm myetlegacy setup
```

Start it:

```bash
alphagsm myetlegacy start
```

Check it:

```bash
alphagsm myetlegacy status
```

Stop it:

```bash
alphagsm myetlegacy stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myetlegacy update
alphagsm myetlegacy backup
```

## Notes

- Module name: `etlegacyserver`
- Default port: 27960
