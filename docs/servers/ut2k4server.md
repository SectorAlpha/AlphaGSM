# Unreal Tournament 2004

This guide covers the `ut2k4server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myut2k4ser create ut2k4server
```

Run setup:

```bash
alphagsm myut2k4ser setup
```

Start it:

```bash
alphagsm myut2k4ser start
```

Check it:

```bash
alphagsm myut2k4ser status
```

Stop it:

```bash
alphagsm myut2k4ser stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myut2k4ser update
alphagsm myut2k4ser backup
```

## Notes

- Module name: `ut2k4server`
- Default port: 7777
