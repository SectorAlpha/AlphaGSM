# Battlefield 1942

This guide covers the `bf1942server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybf1942se create bf1942server
```

Run setup:

```bash
alphagsm mybf1942se setup
```

Start it:

```bash
alphagsm mybf1942se start
```

Check it:

```bash
alphagsm mybf1942se status
```

Stop it:

```bash
alphagsm mybf1942se stop
```

## Setup Details

Setup configures:

- the game port (default 1942)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mybf1942se update
alphagsm mybf1942se backup
```

## Notes

- Module name: `bf1942server`
- Default port: 1942
