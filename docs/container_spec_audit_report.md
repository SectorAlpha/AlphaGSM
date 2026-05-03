Container spec & start-command audit
=================================

Date: 2026-04-27

What I did
- Scanned `src/gamemodules/` for `get_start_command` implementations and ensured each module exports it.
- Added static validators:
  - `scripts/validate_start_commands.py` — checks `get_start_command` return shape
  - `scripts/list_missing_start_commands.py` — lists modules missing `get_start_command`
  - `scripts/validate_container_specs.py` — checks `get_container_spec` implementations reference start commands or builders
- Normalized missing/alias modules by delegating or adding clear `get_start_command` stubs where appropriate.

Files changed (high level)
- Edited many alias modules to delegate `get_start_command` (examples):
  - `src/gamemodules/csgo.py`, `csgoserver.py`, `cs2server.py`, `tf2.py`, `tf2server.py`
  - `src/gamemodules/minecraft/DEFAULT.py`, `terraria/DEFAULT.py`, `arma3/DEFAULT.py`
- Fixed/cleaned: `src/gamemodules/minecraft/jardownload.py`
- Added not-implemented stubs for helper-only modules so static checks are deterministic:
  - `src/gamemodules/factorio.py`
  - `src/gamemodules/minecraft/papermc.py`
  - `src/gamemodules/minecraft/properties_config.py`
  - `src/gamemodules/terraria/common.py`

Why
- The Docker runtime builders expect `get_start_command(server)` to return `(argv_list, working_dir)` so the container spec can be built deterministically. Some modules were alias/wrappers or helpers that didn't expose the symbol; that caused the static inventory to flag them as missing. Normalizing this surface reduces runtime surprises.

Recommended runtime test steps (local)
1. Run the validators to double-check:

```bash
python3 scripts/validate_start_commands.py
python3 scripts/list_missing_start_commands.py
python3 scripts/validate_container_specs.py
```

2. Pick a representative set of modules and ensure `get_container_spec` returns a valid dict. Example interactive check (replace `<module>` and `<server>` with real objects):

```python
from importlib import import_module
mod = import_module('gamemodules.tf2')
class DummyServer:
    def __init__(self):
        self.name = 'test'
        self.data = {'dir': '/srv/server/', 'exe_name': 'srcds_run', 'port': 27015}
server = DummyServer()
spec = mod.get_container_spec(server)
assert isinstance(spec, dict)
assert 'command' in spec and isinstance(spec['command'], (list, tuple))
```

3. For Docker-specific verification, run one module's container spec with Docker (example TF2):

```bash
python3 - <<'PY'
from importlib import import_module
mod = import_module('gamemodules.teamfortress2')
class DummyServer:
    def __init__(self):
        self.name = 'tf2test'
        self.data = {'dir': '/srv/server/', 'exe_name': 'srcds_run', 'port': 27015}
server = DummyServer()
spec = mod.get_container_spec(server)
import json
print(json.dumps(spec, indent=2))
PY

# Then use the printed `spec` to build a Docker `docker run` invocation or test with your container orchestration.
```

Notes and caveats
- These changes are conservative and mostly introduce delegations or NotImplementedError stubs for helper modules. They do not change runtime behaviour for implemented modules.
- Some modules still rely on platform-specific helpers (Proton, SteamCMD). Running container checks on those modules may require additional environment setup.

If you want I can:
- Open a single PR branch with all changes and a concise commit message, or
- Revert patches for any module you prefer to keep unchanged and instead add a documentation-only change.
