# TeamSpeak 3

This guide covers the `ts3server` module in AlphaGSM.

`ts3server` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myts3serve create ts3server
```

Run setup:

```bash
alphagsm myts3serve setup
```

Start it:

```bash
alphagsm myts3serve start
```

Check it:

```bash
alphagsm myts3serve status
```

Stop it:

```bash
alphagsm myts3serve stop
```

## Setup Details

Setup configures:

- the game port (default 10011)
- the install directory

## Useful Commands

```bash
alphagsm myts3serve update
alphagsm myts3serve backup
```

## Notes

- Module name: `ts3server`
- Default port: 10011

<!-- alphagsm-server-variables:start -->

## Server variables

After `create ts3server`, inspect or change these with `set`:

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

- **Executable**: `ts3server`
- **Location**: `<install_dir>/ts3server`
- **Engine**: Custom

The default database is the SQLite file `ts3server.sqlitedb` in the install directory. Set `db_mode` to `mariadb` to use MariaDB instead. With `db_host` left empty, a Docker runtime server starts a private `mariadb:11.5` container on a network that is not published to the host. TeamSpeak reaches it as `database`. An existing MariaDB data directory can be placed at `<install>/.alphagsm/mariadb-data` before the first start; AlphaGSM initializes a new database only when that directory has no `mysql` folder. Set `db_host` to a hostname when MariaDB is already running somewhere else. `db_password` is written to `ts3db_mariadb.ini` and is not placed on the server command line.

```bash
alphagsm myts3 set db_mode mariadb
alphagsm myts3 set db_name ts3
alphagsm myts3 set db_user ts3
alphagsm myts3 set db_password "the database password"
alphagsm myts3 set runtime docker
```

TeamSpeak loads `libmariadb.so.2` from the extracted `redist` directory. MariaDB mode adds that directory to `LD_LIBRARY_PATH` inside the container. The service-console image also installs `libmariadb3`. A previously published runtime image does not gain that package until it is rebuilt.

Smoke and integration validation require an authenticated ServerQuery response:
`alphagsm info --json` must report protocol `ts3`.

AlphaGSM reads first-start ServerQuery credentials from the selected runtime's
logs, including Docker, without displaying them. Recovered credentials are saved
in `serverquery_admin_password.txt` under the install directory with access
restricted to its owner, so replacing the container retains query access. Keep
this file with the server database when moving an installation.

Queries pace their commands to respect TeamSpeak's default flood limit. A health
check takes about two seconds, allowing consecutive `query` and `info` calls
from Docker without requiring an exemption from flood protection. Concurrent
query clients or stricter custom limits still need coordinated polling.

### Server Configuration

- **Config files**: `ts3server.ini`
- **Template**: See [server-templates/ts3server/](../server-templates/ts3server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
