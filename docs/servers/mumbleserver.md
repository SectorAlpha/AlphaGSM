# Mumble

This guide covers the `mumbleserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymumblese create mumbleserver
```

Run setup:

```bash
alphagsm mymumblese setup
```

Start it:

```bash
alphagsm mymumblese start
```

Check it:

```bash
alphagsm mymumblese status
```

Stop it:

```bash
alphagsm mymumblese stop
```

## Setup Details

Setup configures:

- the game port (default 64738)
- the install directory

## Useful Commands

```bash
alphagsm mymumblese update
alphagsm mymumblese backup
```

## Notes

- Module name: `mumbleserver`
- Default port: 64738
