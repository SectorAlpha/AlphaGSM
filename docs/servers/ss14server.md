# Space Station 14

This guide covers the `ss14server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myss14serv create ss14server
```

Run setup:

```bash
alphagsm myss14serv setup
```

Start it:

```bash
alphagsm myss14serv start
```

Check it:

```bash
alphagsm myss14serv status
```

Stop it:

```bash
alphagsm myss14serv stop
```

## Setup Details

Setup configures:

- the game port (default 1212)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myss14serv update
alphagsm myss14serv backup
```

## Notes

- Module name: `ss14server`
- Default port: 1212
