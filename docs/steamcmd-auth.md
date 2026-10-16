# SteamCMD session profiles

AlphaGSM can cache an isolated SteamCMD session for explicitly supported owned-file
acquisition helpers. Create a profile from an interactive Linux terminal:

```bash
alphagsm steam-auth login owned your_steam_username
alphagsm steam-auth status owned
alphagsm steam-auth logout owned
```

SteamCMD asks for the account password and Steam Guard directly in your terminal.
AlphaGSM does not read or save the password, pass it in process arguments, or put
it in server JSON or `alphagsm.conf`. Profile names accept letters, numbers,
underscores and hyphens. Use a separate Steam account with the required licenses
where practical. Game-server tokens such as GSLTs remain separate requirements.

## Where the login runs

The login runs in the AlphaGSM process, from a real terminal:

```bash
alphagsm steam-auth login owned your_steam_username
alphagsm myserver setup --auth-profile owned
alphagsm steam-auth status owned
```

Use the same commands for a host install of the `alphagsm` command, a
standalone binary, or a Python process that imports AlphaGSM. When that
process starts game servers with `[runtime] backend = docker`, SteamCMD still
runs in the AlphaGSM process before the game container starts. The private
profile stays on the host Linux filesystem, outside the server install
directory. AlphaGSM does not mount `steam-auth/` into the game container.
Anonymous SteamCMD client libraries mounted for a `steamcmd-linux` container
are a different directory.

When AlphaGSM itself is the manager container, forwarded commands currently
run with `docker compose exec -T`, which cannot answer SteamCMD's password
prompt. Open a terminal inside the manager and log in there:

```bash
./alphagsm-docker shell
python alphagsm steam-auth login owned your_steam_username
exit
./alphagsm-docker myserver setup --auth-profile owned
```

The profile is stored under `[core] alphagsm_path`, which the wrapper keeps on
the bind-mounted state directory. That directory must record Unix owners and
modes. Keep each server install beside that state directory, not inside
`steam-auth/`. Direct Compose users omit `-T` for the login command:

```bash
docker compose -f docker/manager/compose.yml exec alphagsm python alphagsm steam-auth login owned your_steam_username
```

Profiles use their own SteamCMD installation and home directory under
`~/.alphagsm/steam-auth/PROFILE/`, or the configured `[core] alphagsm_path`.
They do not reuse your desktop Steam installation or its session. SteamCMD's
usual Linux runtime libraries are still required. The manager image already
includes them. The first interactive login downloads Valve's Linux SteamCMD
bootstrap.

Select a profile with `alphagsm myserver setup --auth-profile owned` for a
managed Steam-backed BYO recipe. Setup remembers its name and reuses it when
required files are missing; clear it with `set steam_auth_profile DELETE`.
`assets fetch steam-owned --auth-profile owned` remains the explicit file-only
refresh command. A supported acquisition helper selects the profile for its
download. Those downloads reuse the cached session with prompts disabled, never
fall back to anonymous, and suppress raw SteamCMD output that could contain
session details. Missing, expired, or unentitled sessions fail with a prompt to
log in again or check entitlement. These commands do not automatically migrate
every existing AUTH-gated module to profiles. Password-protected beta branches
are not supported through profiles; branch passwords are never placed in their
process arguments.

`status` reports only whether local profile metadata and a nonempty SteamCMD
cache exist. It recognizes both the isolated `home/Steam/config/config.vdf`
layout and the legacy `runtime/config/config.vdf` layout inside the profile. It does not contact Valve or prove authentication, ownership, or app
access. `logout` removes the selected local cached profile and its isolated
runtime. It does not revoke sessions remotely at Valve. Login, download, and
logout hold a per-profile lock; if another operation is using it, retry later.
The SteamCMD child also holds that lock, so a surviving child keeps logout
blocked even if the manager is killed. Normal cancellation terminates the
SteamCMD process group and waits for its launcher to exit.

The profile directories have mode `0700`; metadata and cached session files
have mode `0600` (runtime executables retain owner execute permission). Unsafe
links, other owners, and special files are rejected. The full parent directory
chain must be owned by your user or root and must prevent other users from
renaming its entries. A trusted sticky directory such as root-owned `/tmp` is
allowed; a writable non-sticky shared directory is rejected. Treat the entire profile as
sensitive: SteamCMD keeps reusable authentication material there. These
permissions protect against other local users, not root or a compromised process
running as you. Avoid copying profiles into ordinary backups, evidence bundles,
shared folders, images, or source control.

The older configured SteamCMD install path remains available for anonymous and
legacy callers. Do not add plaintext Steam account passwords to its settings;
use session profiles where the acquisition helper supports them.

See [server support status](TEST_STATUS.md) for the difference between
**ENABLED (AUTH)** provider requirements and **ENABLED (BYO)** owned assets.

Local tests for those servers are not part of CI. Run them with
[scripts/run_local_auth_tests.sh](../scripts/run_local_auth_tests.sh). The
[local test readme](../local_tests/README.md) lists the unit and integration
commands. Do not put profile directories, passwords, or tokens in git.
