# Life is Feudal: Your Own

This guide covers the `lifeisfeudalserver` module in AlphaGSM.

## Support Status

`lifeisfeudalserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can stage
the server files, but `start` still requires an operator-provided
MySQL/MariaDB service plus matching database details recorded during setup or
via `set`.

## Requirements

- `screen`
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
