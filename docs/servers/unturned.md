# Unturned

This guide covers the `unturned` module in AlphaGSM.

`unturned` is currently `PASSED` in the checked-in support tracker on the
documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane
validates both process and Docker runtimes for this module, while local runs
remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myunturned create unturned
```

Run setup:

```bash
alphagsm myunturned setup
```

Start it:

```bash
alphagsm myunturned start
```

Check it:

```bash
alphagsm myunturned status
```

Stop it:

```bash
alphagsm myunturned stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

AlphaGSM writes native settings to `Servers/<serverid>/Server/Commands.dat`.
The configured base port is used for Steam A2S queries; gameplay uses the next
UDP port. Open both ports when configuring your firewall.

## Useful Commands

```bash
alphagsm myunturned update
alphagsm myunturned backup
```

## Steam Workshop Content

Add an Unturned Workshop item by ID or Steam Community URL, or expand a
collection into validated item IDs:

```bash
alphagsm myunturned mod add workshop 2396897717
alphagsm myunturned mod add workshop-collection COLLECTION_ID_OR_URL
alphagsm myunturned mod list
alphagsm myunturned mod apply
```

AlphaGSM checks each item's game identity against Unturned's Workshop AppID
`304930`, separately from the dedicated-server download AppID `1110390`.
Applying content writes integer `File_IDs` in
`Servers/<serverid>/WorkshopDownloadConfig.json`. Setup and prestart apply
desired content automatically. Unturned downloads the items and dependencies
during its next startup and supplies required content to connecting players,
as described in the [official server hosting guide](https://docs.smartlydressedgames.com/en/stable/servers/server-hosting.html#steam-workshop-mods).
Restart a running server after applying changes.

For a Workshop map, also select its exact map name with a `Map` line in
`Servers/<serverid>/Server/Commands.dat`. For example, item `2396897717` is
`PEI Arena`; replace any existing `Map` line with `Map PEI Arena`.
`mod apply` configures startup activation; download or config-file presence
alone does not prove the running engine has loaded the content. Check the
live map with `alphagsm myunturned info --json`.

Remove a managed item from activation:

```bash
alphagsm myunturned mod remove workshop 2396897717
alphagsm myunturned mod apply
```

Choose another map before restarting if the removed item supplied the selected
map. `mod cleanup` removes AlphaGSM's native activation entries. Existing
operator IDs and unrelated JSON settings are preserved, and the engine's
download cache is left intact. An anonymously installable dedicated server
does not guarantee access to every Workshop item; inaccessible metadata or
content remains a failure to resolve or load.

## Notes

- Module name: `unturned`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create unturned`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `ServerHelper.sh`
- **Location**: `<install_dir>/ServerHelper.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1110390`

### Server Configuration

- **Config files**: `Servers/<serverid>/Server/Commands.dat` and `Servers/<serverid>/WorkshopDownloadConfig.json`
- **Template**: See [server-templates/unturned/](../server-templates/unturned/) if available

### Maps and Mods

- **Built-in map directory**: `Maps/`
- **Native Workshop cache**: `Servers/<serverid>/Workshop/Steam/`
- **Workshop support**: Native `WorkshopDownloadConfig.json` activation through `mod`

### Workshop Load Validation

The optional Workshop integration cases use a fresh install and the retired
Workshop-only `PEI Arena` map. They require an A2S response naming that map,
then prove shutdown and managed activation removal. Both process and Docker
cases run the lifecycle through AlphaGSM commands:

```bash
PYTHONPATH=.:src ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 ALPHAGSM_RUN_WORKSHOP=1 \
  python -m pytest tests/integration_tests/test_unturned.py -k workshop -v
```

Docker requires a working daemon and a SteamCMD Linux runtime image. Prefer a
branch-local build selected with
`ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX`. For the process smoke runner:

```bash
ALPHAGSM_RUN_WORKSHOP=1 make smoke-test SMOKE_TEST=run_unturned.sh
```

These are opt-in verification paths; the base module's `PASSED` status is not
evidence that a Workshop load test has passed on your host.
