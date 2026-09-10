# Updating Servers And AlphaGSM

There are two different updates:

1. **The game server** — SteamCMD or the game's own files (`alphagsm <name> update`)
2. **AlphaGSM itself** — the manager binary or git checkout (`alphagsm self-update`)

They are separate commands on purpose.

## Update a game server

For Steam games such as TF2, Palworld, and HL2DM:

```bash
alphagsm mytf2 update
```

That stops the server if it is running, re-downloads the dedicated files with
SteamCMD, and leaves the server stopped. Start it again yourself, or ask
AlphaGSM to restart it:

```bash
alphagsm mytf2 update -r
```

`-v` / `--validate` tells SteamCMD to verify the install after the update:

```bash
alphagsm mytf2 update -v
```

You can combine them: `alphagsm mytf2 update -v -r`.

Minecraft and similar download-URL games are not SteamCMD updates. Change the
version or URL with `set`, then run `setup` again. See the matching server
guide.

After any upgrade, `doctor` is a good check:

```bash
alphagsm mytf2 doctor
```

## Update AlphaGSM itself

```bash
alphagsm self-update --check
alphagsm self-update
```

AlphaGSM picks the source automatically:

| How you installed AlphaGSM | What `self-update` does |
| --- | --- |
| Standalone release binary | Downloads the latest GitHub release for this OS/CPU, checks the SHA-256, and replaces the executable |
| Git checkout on `master`, `main`, or a `release*` branch | Fast-forwards to the tracked upstream commit |

It refuses a git self-update when:

- you are on a developer branch
- the working tree is dirty
- the checkout has diverged from upstream
- HEAD is detached

Force the source if auto-detect is wrong:

```bash
alphagsm self-update --source binary
alphagsm self-update --source git
```

For a standalone binary, the install directory must be writable. On Windows,
replacement is scheduled for after the CLI exits; the command prints a result
file to confirm it. A failed update keeps the previous executable.

Restart running game servers after an AlphaGSM upgrade if you want them to use
the new manager behaviour (especially subprocess console input).

## Install or replace the standalone binary

Download the executable for your OS and CPU from
[GitHub Releases](https://github.com/SectorAlpha/AlphaGSM/releases). Keep the
matching `.sha256` file if you want to verify it.

```bash
chmod +x alphagsm
./alphagsm --version
./alphagsm --help
```

On Windows, use `.\alphagsm.exe`. Full platform notes, checksums, and first-run
paths are in [Standalone Binaries](standalone-binaries.md).

You do not need a Python install for the release binary. Game servers still
need their own runtime (Java, SteamCMD libraries, or Docker).
