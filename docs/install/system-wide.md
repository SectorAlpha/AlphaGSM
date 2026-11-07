# System-Wide Install

Use this path on a shared Linux machine. It installs the AlphaGSM program
once. People on the machine then run that same `alphagsm` command.

The shared part is the program and the download cache. Each person's servers,
logs, and backups stay in that person's home directory, normally
`~/.alphagsm`. This install does not put everyone's game servers into one
account.

Windows and macOS are not covered here.

## What the installer prepares

Run as root:

```bash
sudo bash ./scripts/install-system-wide.sh
```

On a new machine it does all of the following.

- Creates a system account named `alphagsm` when that account is missing.
  The account gets a home directory and cannot log in.
- Copies the program to `/usr/local/lib/alphagsm`.
- Links `/usr/local/bin/alphagsm` at that program.
- Installs `/usr/local/sbin/gitalphagsm` for root.
- Creates `/etc/alphagsm.conf` from `alphagsm.conf-template` when that file
  is missing.
- Turns on the shared download cache in a new config file.
- Writes `/etc/sudoers.d/gameservers` and checks it with `visudo` when
  `visudo` is installed.
- Creates `/home/alphagsm/downloads` and `/home/alphagsm/gitlive`.

The copy leaves out a local `alphagsm.conf`, `env`, `.venv`, and
`__pycache__`. It keeps `.git` when the checkout has one. Running the script
again refreshes the program and does not replace an existing
`/etc/alphagsm.conf`.

Install the Python packages before the first real command. The script does
not install them:

```bash
sudo python3 -m pip install --break-system-packages -r requirements-runtime.txt
```

Use the package names from
[host install requirements](../../README.md#host-install-requirements) when a
game asks for Java or system libraries.

## Paths

| Path | Role |
| --- | --- |
| `/usr/local/lib/alphagsm` | Copied program |
| `/usr/local/bin/alphagsm` | Command used by every operator. It points at the copied program, and AlphaGSM follows that link to find `src`. |
| `/etc/alphagsm.conf` | Config read by this install |
| `/home/alphagsm` | Home of the download account |
| `/home/alphagsm/downloads/downloads.txt` | Shared download database |
| `/home/alphagsm/downloads/downloads` | Shared download files |
| `/home/alphagsm/gitlive` | Empty directory for an operator checkout |
| `/usr/local/sbin/gitalphagsm` | Root helper that runs git in the program directory |
| `/etc/sudoers.d/gameservers` | Passwordless sudo for the shared downloader |

AlphaGSM reads `/etc/alphagsm.conf` because the program file is under `/usr`.
The same build, copied anywhere else, reads `alphagsm.conf` beside the
program instead. `ALPHAGSM_CONFIG_LOCATION` overrides that choice for one
command.

## Shared downloads

A new `/etc/alphagsm.conf` contains:

```ini
[downloader]
user = alphagsm
db_path = /home/alphagsm/downloads/downloads.txt
target_path = /home/alphagsm/downloads/downloads
```

With `user` set, a missing file is downloaded by the `alphagsm` account.
AlphaGSM runs:

```bash
sudo -Hu alphagsm /usr/local/lib/alphagsm/alphagsm-downloads MODULE ARGS
```

The sudoers entry allows that one command with no password for members of
the `alphagsm` group:

```text
%alphagsm ALL = (alphagsm) NOPASSWD:/usr/local/lib/alphagsm/alphagsm-downloads
```

Add each person who will run servers:

```bash
sudo usermod -aG alphagsm USER
```

That person starts a new login before the group applies. People outside the
group can still run `alphagsm`, but the first download of a file asks for a
password through `sudo`.

If `/etc/alphagsm.conf` already existed, the installer leaves it alone. Set
the three `downloader` keys yourself to use the shared cache.

`/home/alphagsm/gitlive` is only a directory. AlphaGSM does not clone into it
or read it. Use it when you want a shared checkout that is separate from the
copy under `/usr/local/lib/alphagsm`.

## Each person's servers

Creating a server writes that server under the account that ran the command.
Two people on the same machine get two homes and two server lists. They share
downloaded archives through the `alphagsm` account, so the second setup can
reuse a file the first setup already fetched.

Per-person settings still live in `~/.alphagsm`, including the server list.
Change `alphagsm_path` in the user settings only when an account should keep
servers somewhere else.

## Update the program

When the copy contains `.git`, root can update it:

```bash
sudo gitalphagsm pull
```

`gitalphagsm` runs `git` in `/usr/local/lib/alphagsm` and then stops. It does
not restart game servers. If that directory has no `.git`, the helper exits
and tells you. Run `sudo bash ./scripts/install-system-wide.sh` from a newer
checkout instead.

## Check the layout without touching the host

From a machine with Docker:

```bash
bash ./system_install_tests/run_system_install_in_container.sh
```

That starts Ubuntu 24.04, installs Python and the runtime packages, runs the
system installer, checks the paths and sudoers file, runs the installer a
second time to prove the existing config is kept, and runs `alphagsm --help`.
The host's `/etc` and `/usr/local` are not changed.
