# GRAV

This guide covers the `gravserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygravserv create gravserver
```

Run setup:

```bash
alphagsm mygravserv setup
```

Start it:

```bash
alphagsm mygravserv start
```

Check it:

```bash
alphagsm mygravserv status
```

Stop it:

```bash
alphagsm mygravserv stop
```

## Setup Details

Setup configures:

- the game port (default 7778)
- the install directory

## Useful Commands

```bash
alphagsm mygravserv update
alphagsm mygravserv backup
```

## Notes

- Module name: `gravserver`
- Default port: 7778
