# RimWorld Together

This guide covers the `rimworldtogetherserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myrimworld create rimworldtogetherserver
```

Run setup:

```bash
alphagsm myrimworld setup
```

Start it:

```bash
alphagsm myrimworld start
```

Check it:

```bash
alphagsm myrimworld status
```

Stop it:

```bash
alphagsm myrimworld stop
```

## Setup Details

Setup configures:

- the game port (default 25555)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myrimworld update
alphagsm myrimworld backup
```

## Notes

- Module name: `rimworldtogetherserver`
- Default port: 25555
