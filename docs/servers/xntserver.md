# Xonotic

This guide covers the `xntserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myxntserve create xntserver
```

Run setup:

```bash
alphagsm myxntserve setup
```

Start it:

```bash
alphagsm myxntserve start
```

Check it:

```bash
alphagsm myxntserve status
```

Stop it:

```bash
alphagsm myxntserve stop
```

## Setup Details

Setup configures:

- the game port (default 26000)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myxntserve update
alphagsm myxntserve backup
```

## Notes

- Module name: `xntserver`
- Default port: 26000
