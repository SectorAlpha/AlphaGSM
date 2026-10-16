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

Profiles use their own SteamCMD installation and home directory under
`~/.alphagsm/steam-auth/PROFILE/`, or the configured `[core] alphagsm_path`.
They do not reuse your desktop Steam installation or its session. The current
installer runs on the Linux host; selecting Docker for a game does not move
this login into a container. SteamCMD's usual Linux runtime libraries are still
required. The first interactive login downloads Valve's Linux SteamCMD bootstrap.

A supported acquisition helper must explicitly select the profile for its
download. Those downloads reuse the cached session with prompts disabled, never
fall back to anonymous, and suppress raw SteamCMD output that could contain
session details. Missing, expired, or unentitled sessions fail with a prompt to
log in again or check entitlement. These commands do not automatically migrate
every existing AUTH-gated module to profiles. Password-protected beta branches
are not supported through profiles; branch passwords are never placed in their
process arguments.

`status` reports only whether local profile metadata and SteamCMD cache files
exist. It does not contact Valve or prove authentication, ownership, or app
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
