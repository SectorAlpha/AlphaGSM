# arma3.headless

This guide covers the `arma3.headless` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myheadless create arma3.headless
```

Run setup:

```bash
alphagsm myheadless setup
```

Start it:

```bash
alphagsm myheadless start
```

Check it:

```bash
alphagsm myheadless status
```

Stop it:

```bash
alphagsm myheadless stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm myheadless update
alphagsm myheadless backup
```

## Notes

- Module name: `arma3.headless`
- Default port: 27015
