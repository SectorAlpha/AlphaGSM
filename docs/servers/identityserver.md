# Identity

This guide covers the `identityserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myidentity create identityserver
```

Run setup:

```bash
alphagsm myidentity setup
```

Start it:

```bash
alphagsm myidentity start
```

Check it:

```bash
alphagsm myidentity status
```

Stop it:

```bash
alphagsm myidentity stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myidentity update
alphagsm myidentity backup
```

## Notes

- Module name: `identityserver`
- Default port: 7777
