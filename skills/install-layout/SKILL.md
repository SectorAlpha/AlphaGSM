# Install Layout

| Field | Value |
| --- | --- |
| Purpose | Keep per-server install directories predictable so setup, docs, tests, and updates all agree about where files live. |
| Use when | Adding or changing `configure()`, `install()`, archive extraction, executable lookup, or config-file documentation. |
| Main source | The game module's `configure()`, `install()`, and `get_start_command()` functions, plus smoke tests and `utils/archive_install.py`. |

| Field | Value |
| --- | --- |
| Inputs | Game module install code, on-disk server tree, stored `server.data` keys, and user-facing docs/templates. |
| Outputs | A stable install layout, correct stored paths, and docs/tests that point at the real executable and config files. |
| Related files | `src/gamemodules/**`, `src/utils/archive_install.py`, `docs/server-templates/**`, `docs/servers/*.md`, `tests/smoke_tests/*.sh`. |

Use this skill when validating where AlphaGSM installs a server and how the module refers to files inside that install.

## Standard Expectations

- `server.data["dir"]` points at the install root the user chose during `setup`.
- The start command resolves an executable that actually exists inside that install.
- Config files are either in a conventional location or stored explicitly in `server.data`, and docs/templates should mirror that real path and filename.
- Archive-backed installs should be flattened into a stable root rather than leaving versioned wrapper directories in the way.
- Smoke tests, integration tests, and docs should all point at the same on-disk layout.

## What To Check

1. `configure()` stores the install directory and any non-obvious file paths.
2. `install()` writes files into the intended root and calls `server.data.save()`.
3. `get_start_command()` returns the correct executable path and working directory.
4. Any generated config file path matches the path described in `docs/servers/` and `docs/server-templates/`, including the filename and subpath.
5. Updates and restarts still work after the initial install layout is established.

## Common Failure Modes

- The archive extracts into `game-1.2.3/` but the module expects files at the install root.
- `exe_name` is stored, but the real binary lives in a subdirectory the module never joins.
- Docs or templates describe `server.cfg` in one place while the module writes or reads a different file.
- A template uses `alphagsm-example.cfg` even though the module or guide already names a stable real config file.
- Smoke tests patch files under one path while `start` reads another.

## Preferred Fixes

- Normalize archive extraction so the install root matches the module's expectations.
- Store unusual executable or config paths explicitly instead of rediscovering them in multiple places.
- Reuse shared helpers such as `utils/archive_install.py` where possible instead of bespoke copy trees.
- Update docs immediately after the real install path changes.
- Rename server-template files to the real runtime filename whenever the module or verified docs establish one stable config path.
