# Local User Install

Use this path on Linux when one person runs AlphaGSM from their own account.

The script copies the repository, writes a config file if you do not already
have one, and links `alphagsm` into `~/.local/bin`. It does not install Python
packages, system libraries, Java, or SteamCMD. It does not share downloads
with other accounts.

Windows and macOS are not covered here. On those systems, run AlphaGSM from a
checkout or use a standalone binary. See
[Getting Started](../../README.md).

## Before you run it

Install Python 3 and the runtime packages from the repository:

```bash
python3 -m pip install -r requirements-runtime.txt
```

`requirements.txt` is the wider set used for development and tests. A normal
server only needs `requirements-runtime.txt`.

Game servers may also need Java, 32-bit libraries, or other host packages.
The [host install requirements](../../README.md#host-install-requirements)
list the common ones. AlphaGSM reports a missing host package when you start
a server that needs it.

## Run it

From the repository root:

```bash
bash ./scripts/install-local-user.sh
```

The copy leaves out a local `alphagsm.conf`, `env`, `.venv`, and
`__pycache__`. It keeps `.git` when the checkout has one. Running the script
again refreshes the copied code and does not replace an existing
`~/.local/lib/alphagsm/alphagsm.conf`.

## Paths

| Path | Role |
| --- | --- |
| `~/.local/lib/alphagsm` | Copied program |
| `~/.local/bin/alphagsm` | Command link. It points at the copied program, and AlphaGSM follows that link to find `src`. |
| `~/.local/lib/alphagsm/alphagsm.conf` | Config read by this install |

AlphaGSM chooses that config because the code does not live under `/usr`. A
copy installed under `/usr`, including `/usr/local`, reads `/etc/alphagsm.conf`
instead. See [System-Wide Install](system-wide.md).

`ALPHAGSM_CONFIG_LOCATION` still overrides the config file for one command.

If `~/.local/bin` is not already on your `PATH`, add it to your shell profile:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Open a new shell, then check the command:

```bash
alphagsm --help
```

## First server

Follow the [Fast Start](../../README.md#fast-start) commands. Use `alphagsm`
instead of `./alphagsm` once the link is on your `PATH`. For example:

```bash
alphagsm mymc create minecraft.vanilla
alphagsm mymc setup
alphagsm mymc start
alphagsm mymc query
alphagsm mymc stop
```

Servers, logs, and backups for this account stay under `~/.alphagsm` unless
the config changes `alphagsm_path`. Downloads stay in this account too. There
is no shared download user.

## Update the copy

When the install still contains `.git`:

```bash
git -C "$HOME/.local/lib/alphagsm" pull
```

Otherwise run `bash ./scripts/install-local-user.sh` again from a newer
checkout. Neither path edits your existing config file.
