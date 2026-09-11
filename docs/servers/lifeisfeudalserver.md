# Life is Feudal: Your Own

This guide covers the `lifeisfeudalserver` module in AlphaGSM.

## Support Status

`lifeisfeudalserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can stage
the server files, but `start` still requires an operator-provided
MySQL/MariaDB service plus matching database details recorded during setup or
via `set`. This checked-in support state is validated against the documented
Ubuntu 24.04 Linux baseline. The current GitHub validation shape uses the
Docker Wine/Proton path for smoke coverage, while the integration lane still
exercises both process and Docker runtime selection around that external
database prerequisite.

## Requirements

- `screen` for the host-process runtime path
- a Docker engine plus the AlphaGSM Wine/Proton runtime image for the
  Docker-backed runtime path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- a reachable MySQL or MariaDB service
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mylifeisfe create lifeisfeudalserver
```

Run setup:

```bash
alphagsm mylifeisfe setup
```

Start it:

```bash
alphagsm mylifeisfe start
```

Check it:

```bash
alphagsm mylifeisfe status
```

Stop it:

```bash
alphagsm mylifeisfe stop
```

## Setup Details

Setup configures:

- the game port (default 28001)
- the install directory
- the database host, port, name, user, and password
- SteamCMD downloads the server files
- AlphaGSM copies or refreshes `config_local.cs` from the shipped
  `docs/config_local.cs` template when it is available
- AlphaGSM starts world 1 and synchronizes its game port in `config/world_1.xml`,
  preserving the other shipped world settings. Queries use Steam A2S on the
  game port plus two; all three adjacent ports are claimed together.

The world, database routing, and query corrections await replacement CI
validation. With `db_mode docker`, AlphaGSM waits for the managed MariaDB
container to answer SQL before starting the game. A game on Docker's default
bridge uses the database container's bridge address; a host process uses its
published database port. Custom Docker networks are not supported for this
managed database mode.

For a fresh world, let the game create the `lif_1` schema; the managed database
mode provisions credentials without creating an empty world database. Existing
database contents are preserved. This follows the [dedicated-server setup guide](https://kb.feudal.tools/knowledge-base/setup-lifyo-dedicated-server-on-ubuntu-linux/).
The current launch selects world 1; changing `db_name` does not select another
world, so use `lif_1` for this flow.

## Bring Your Own Steps

1. Run `alphagsm mylifeisfe create lifeisfeudalserver`.
2. Run `alphagsm mylifeisfe setup` and record the MySQL/MariaDB host, port,
   database name, user, and password that the server should use.
3. Provision that database locally or publish it from Docker to a reachable
   host and port before running `alphagsm mylifeisfe start`.
4. Keep that database service running while AlphaGSM manages the server.
5. If you change database details later, update them with:

```bash
alphagsm mylifeisfe set db_host 127.0.0.1
alphagsm mylifeisfe set db_port 3306
alphagsm mylifeisfe set db_name lif_1
alphagsm mylifeisfe set db_user root
alphagsm mylifeisfe set db_password your-password
```

If `start` reports an `ENABLED (BYO)` database requirement, verify that the
configured endpoint is reachable and that the copied `config_local.cs` values
match the database you provisioned.

## Useful Commands

```bash
alphagsm mylifeisfe update
alphagsm mylifeisfe backup
```

## Notes

- Module name: `lifeisfeudalserver`
- Default port: 28001

<!-- alphagsm-server-variables:start -->

## Server variables

After `create lifeisfeudalserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `db_host` | databasehost, mysqlhost, mariadbhost | string | Hostname or IP address for the Life is Feudal MySQL/MariaDB service. Example: `127.0.0.1`. |
| `db_mode` | databasemode | string | Whether Life is Feudal should use a locally managed database or an AlphaGSM-managed Docker MariaDB. Example: `local`. |
| `db_name` | database, databasename | string | Database/schema name used by Life is Feudal. Example: `lif_1`. |
| `db_password` | databasepassword, mysqlpassword, mariadbpassword | string | Database password used by Life is Feudal. Stored as a secret. |
| `db_port` | databaseport, mysqlport, mariadbport | integer | TCP port for the Life is Feudal MySQL/MariaDB service. Example: `3306`. |
| `db_user` | databaseuser, mysqluser, mariadbuser | string | Database login used by Life is Feudal. Example: `root`. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `ddctd_cm_yo_server.exe`
- **Location**: `<install_dir>/ddctd_cm_yo_server.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `320850`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/lifeisfeudalserver/](../server-templates/lifeisfeudalserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
