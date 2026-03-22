# minecraft.paper

This guide covers the `minecraft.paper` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypaper create minecraft.paper
```

Run setup:

```bash
alphagsm mypaper setup
```

Start it:

```bash
alphagsm mypaper start
```

Check it:

```bash
alphagsm mypaper status
```

Stop it:

```bash
alphagsm mypaper stop
```

## Setup Details

Setup configures:

- the game port (default 25565)
- the install directory

## Useful Commands

```bash
alphagsm mypaper update
alphagsm mypaper backup
```

## Notes

- Module name: `minecraft.paper`
- Default port: 25565
