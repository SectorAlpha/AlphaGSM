# BYO Enabled Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class `ENABLED (BYO)` support state that counts bring-your-own servers as supported, removes them from the disabled gate, and shows explicit operator guidance in the console and docs.

**Architecture:** Add a separate repository source of truth for BYO-enabled modules, teach the server/module gate and support-tracker generator about that new state, then migrate the already-proven bring-your-own backlog to the new section with explicit per-module guidance. Keep the change layered so support-state plumbing lands before module migrations.

**Tech Stack:** Python, markdown docs, shell smoke helpers, existing AlphaGSM module lifecycle hooks

---

### Task 1: Add BYO Support-State Plumbing

**Files:**
- Create: `enabled_byo_servers.conf`
- Modify: `src/server/server.py`
- Modify: `tests/unit_tests/server/test_server.py`

- [ ] **Step 1: Write the failing loader and create-gate tests**

Add tests in `tests/unit_tests/server/test_server.py` for:

```python
def test_load_enabled_byo_servers_parses_reasons(monkeypatch, tmp_path):
    enabled_path = tmp_path / "enabled_byo_servers.conf"
    enabled_path.write_text(
        "cod2server\tcopy localized_*.iwd and default_localize_mp.cfg into <install_dir>/main/\n"
        "minecraft.custom\tplace a server jar at <install_dir>/<exe_name>\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(server_module, "_ENABLED_BYO_SERVERS_PATH", str(enabled_path))

    assert server_module._load_enabled_byo_servers() == {
        "cod2server": "copy localized_*.iwd and default_localize_mp.cfg into <install_dir>/main/",
        "minecraft.custom": "place a server jar at <install_dir>/<exe_name>",
    }


def test_findmodule_allows_enabled_byo_module(monkeypatch):
    real_module = SimpleNamespace(__file__="/tmp/real.py")

    class FakeCatalog:
        def resolve(self, name):
            return "cod2server"

    monkeypatch.setattr(server_module, "MODULE_CATALOG", FakeCatalog(), raising=False)
    monkeypatch.setattr(server_module, "_load_disabled_servers", lambda: {})
    monkeypatch.setattr(
        server_module,
        "_load_enabled_byo_servers",
        lambda: {"cod2server": "copy assets"},
    )
    monkeypatch.setattr(server_module, "import_module", lambda name: real_module)
    monkeypatch.setattr(server_module.runtime_module, "ensure_runtime_hooks", lambda module: None)

    resolved_name, resolved_module = server_module._findmodule("cod2server")

    assert resolved_name == "cod2server"
    assert resolved_module is real_module
```

- [ ] **Step 2: Run the focused server-loader tests and confirm failure**

Run:

```bash
python3 -m pytest tests/unit_tests/server/test_server.py -q
```

Expected: failure for missing `_ENABLED_BYO_SERVERS_PATH` / `_load_enabled_byo_servers`.

- [ ] **Step 3: Implement the BYO loader and keep disabled gating intact**

Add to `src/server/server.py`:

```python
_ENABLED_BYO_SERVERS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "enabled_byo_servers.conf",
)


def _load_status_reason_file(path):
    rows = {}
    if not os.path.isfile(path):
        return rows
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            module_name = parts[0].strip()
            reason = parts[1].strip() if len(parts) > 1 else "No reason given"
            rows[module_name] = reason
    return rows


def _load_disabled_servers():
    return _load_status_reason_file(_DISABLED_SERVERS_PATH)


def _load_enabled_byo_servers():
    return _load_status_reason_file(_ENABLED_BYO_SERVERS_PATH)
```

Keep `_findmodule(...)` blocking only modules in `_load_disabled_servers()`.

- [ ] **Step 4: Seed the new source-of-truth file**

Create `enabled_byo_servers.conf` with an initial header and starter rows:

```text
# Enabled bring-your-own game server modules
# Format: module_name<TAB>reason
```

Do not migrate entries yet in this task; only establish the file and parser.

- [ ] **Step 5: Re-run the focused loader tests**

Run:

```bash
python3 -m pytest tests/unit_tests/server/test_server.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add enabled_byo_servers.conf src/server/server.py tests/unit_tests/server/test_server.py
git commit -m "Add enabled BYO support-state loader"
```

### Task 2: Teach Trackers And Support Matrix About ENABLED (BYO)

**Files:**
- Modify: `scripts/generate_game_server_support_tracker.py`
- Modify: `docs/TEST_STATUS.md`
- Modify: `docs/game-server-support.md`
- Test: `tests/unit_tests/test_game_server_support_tracker.py`

- [ ] **Step 1: Write failing tracker-parser tests**

Create `tests/unit_tests/test_game_server_support_tracker.py` with:

```python
from scripts.generate_game_server_support_tracker import parse_status_sections, render_support_tracker


def test_parse_status_sections_includes_enabled_byo():
    text = """
## PASSED (1)
| Test | Type |
|------|------|
| acserver | SteamCMD |

## ENABLED (BYO) (2)
| Test | Type |
|------|------|
| cod2server | bring-your-own-assets |
| dstserver | bring-your-own-config |

## DISABLED (1)
| Test | Type |
|------|------|
| bfvserver | dead URL |
"""
    rows = parse_status_sections(text)
    assert rows["PASSED"] == ["acserver"]
    assert rows["ENABLED (BYO)"] == ["cod2server", "dstserver"]
    assert rows["DISABLED"] == ["bfvserver"]


def test_render_support_tracker_counts_enabled_byo_as_supported():
    rows = {
        "PASSED": ["acserver"],
        "ENABLED (BYO)": ["cod2server"],
        "DISABLED": ["bfvserver"],
        "SKIPPED": ["stormworksserver"],
    }
    rendered = render_support_tracker(rows)
    assert "## Supported Now" in rendered
    assert "- [x] acserver" in rendered
    assert "- [x] cod2server" in rendered
```

- [ ] **Step 2: Run the new tracker tests and confirm failure**

Run:

```bash
python3 -m pytest tests/unit_tests/test_game_server_support_tracker.py -q
```

Expected: failure because `ENABLED (BYO)` is unknown.

- [ ] **Step 3: Implement the new section in the generator**

Update `scripts/generate_game_server_support_tracker.py`:

```python
SECTIONS = (
    ("PASSED", "Supported Now", "[x]"),
    ("ENABLED (BYO)", "Supported Now", "[x]"),
    ("DISABLED", "Not Currently Supported", "[ ]"),
    ("SKIPPED", "Waiting On Prerequisites Or Validation", "[ ]"),
)
```

Keep `parse_status_sections(...)` and `render_support_tracker(...)` generic enough to handle the extra section.

- [ ] **Step 4: Update the checked-in tracker format**

Edit `docs/TEST_STATUS.md`:

- add `ENABLED (BYO)` to the legend
- add a new `## ENABLED (BYO)` section between `PASSED` and `DISABLED`
- add a new summary row for `ENABLED (BYO)`
- keep `SUPPORTED = PASSED + ENABLED (BYO)` implicit through the support matrix

- [ ] **Step 5: Regenerate and verify the support matrix**

Run:

```bash
python3 scripts/generate_game_server_support_tracker.py
python3 scripts/generate_game_server_support_tracker.py --check
python3 -m pytest tests/unit_tests/test_game_server_support_tracker.py -q
```

Expected: PASS and regenerated `docs/game-server-support.md`.

- [ ] **Step 6: Commit**

```bash
git add scripts/generate_game_server_support_tracker.py docs/TEST_STATUS.md docs/game-server-support.md tests/unit_tests/test_game_server_support_tracker.py
git commit -m "Add ENABLED BYO tracker status"
```

### Task 3: Add Shared BYO Console Guidance

**Files:**
- Modify: `src/server/errors.py` or `src/server/server.py`
- Modify: `src/utils/gamemodules/common.py`
- Test: `tests/unit_tests/gamemodules/test_common_helpers.py`

- [ ] **Step 1: Write failing tests for a reusable BYO error helper**

Add focused tests in `tests/unit_tests/gamemodules/test_common_helpers.py`:

```python
def test_raise_byo_requirement_formats_guidance():
    with pytest.raises(ServerError) as exc_info:
        common.raise_byo_requirement(
            "cod2server",
            "copy localized_*.iwd and default_localize_mp.cfg into <install_dir>/main/",
        )
    message = str(exc_info.value)
    assert "ENABLED (BYO)" in message
    assert "cod2server" in message
    assert "localized_*.iwd" in message
```

- [ ] **Step 2: Run the focused helper tests and confirm failure**

Run:

```bash
python3 -m pytest tests/unit_tests/gamemodules/test_common_helpers.py -q
```

Expected: missing helper failure.

- [ ] **Step 3: Implement the helper**

Add to `src/utils/gamemodules/common.py`:

```python
def raise_byo_requirement(module_name, guidance):
    raise ServerError(
        "Server module '{}' is supported in ENABLED (BYO) mode.\n"
        "Bring your own requirement: {}\n"
        "Once the required assets/config are present, rerun the AlphaGSM command."
        .format(module_name, guidance)
    )
```

Use the existing `ServerError` import pattern already present in that file or add it if needed.

- [ ] **Step 4: Re-run the focused helper tests**

Run:

```bash
python3 -m pytest tests/unit_tests/gamemodules/test_common_helpers.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/utils/gamemodules/common.py tests/unit_tests/gamemodules/test_common_helpers.py
git commit -m "Add shared BYO guidance helper"
```

### Task 4: Migrate The First BYO Backlog Slice

**Files:**
- Modify: `enabled_byo_servers.conf`
- Modify: `disabled_servers.conf`
- Modify: `docs/TEST_STATUS.md`
- Modify: `docs/servers/cod2server.md`
- Modify: `docs/servers/cod4server.md`
- Modify: `docs/servers/coduoserver.md`
- Modify: `docs/servers/dstserver.md`
- Modify: `docs/servers/minecraft-custom.md`
- Modify: `docs/servers/mxbikesserver.md`
- Modify: `docs/servers/qlserver.md`
- Modify: `docs/servers/rtcwserver.md`
- Modify: `docs/servers/subnauticaserver.md`
- Modify module files that should raise shared BYO guidance early
- Modify matching skipped integration headers / smoke headers if they still say `Disabled`
- Modify: `changelog.txt`

- [ ] **Step 1: Move proven BYO rows into the new source of truth**

Add these initial rows to `enabled_byo_servers.conf` with the same operator guidance already proven in `docs/TEST_STATUS.md`:

```text
cod2server\tcopy localized_*.iwd plus default_localize_mp.cfg into <install_dir>/main/
cod4server\tcopy fileSysCheck.cfg into <install_dir>/ and main/localized_*.iwd into <install_dir>/main/
coduoserver\tcopy pak0.pk3 or default_mp.cfg into <install_dir>/main/
dstserver\tplace cluster_token.txt plus cluster config under <install_dir>/<confdir>/<cluster>/
minecraft.custom\tplace a real server jar at <install_dir>/<exe_name> and set exe_name
mxbikesserver\tprovide a direct dedicated-server archive URL through setup or set url
qlserver\tuse owned/authenticated Quake Live access plus required server auth/config
rtcwserver\tcopy mp_bin.pk3, mp_pak0.pk3- mp_pak5.pk3, and mp_pakmaps0.pk3- mp_pakmaps6.pk3 into main/
subnauticaserver\tsupply a real Subnautica installation path for Nitrox
```

Remove those same modules from `disabled_servers.conf`.

- [ ] **Step 2: Add fail-fast BYO guidance to the migrated modules**

For each migrated module, use the shared helper at the exact validation point where the required asset/config is known missing. Example pattern:

```python
if not os.path.isfile(required_path):
    gamemodule_common.raise_byo_requirement(
        "cod2server",
        "Copy localized_*.iwd and default_localize_mp.cfg into <install_dir>/main/ and retry start.",
    )
```

Prefer existing `install`, `prestart`, or `get_start_command` validation hooks rather than inventing new lifecycle stages.

- [ ] **Step 3: Update tracker rows and section counts**

Move the migrated servers into `## ENABLED (BYO)` in `docs/TEST_STATUS.md` and update summary counts. Keep the exact reason text aligned with `enabled_byo_servers.conf`.

- [ ] **Step 4: Update operator guides and smoke/integration wording**

For every migrated server:

- guide says it is supported in `ENABLED (BYO)` mode
- guide lists exact files/paths/settings to provide
- smoke/integration skip headers stop calling the module “disabled” if it is now BYO-enabled

- [ ] **Step 5: Regenerate and verify**

Run:

```bash
python3 scripts/generate_game_server_support_tracker.py
python3 scripts/generate_game_server_support_tracker.py --check
python3 -m pytest tests/unit_tests/server/test_server.py tests/unit_tests/test_game_server_support_tracker.py tests/unit_tests/gamemodules/test_common_helpers.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add enabled_byo_servers.conf disabled_servers.conf docs/TEST_STATUS.md docs/game-server-support.md docs/servers/ cod2server... cod4server... coduoserver... dstserver... minecraft-custom... mxbikesserver... qlserver... rtcwserver... subnauticaserver... src/gamemodules/... tests/... changelog.txt
git commit -m "Promote supported bring-your-own servers"
```

### Task 5: Final Verification

**Files:**
- Modify: any touched files from earlier tasks only if verification finds issues

- [ ] **Step 1: Run the focused verification suite**

Run:

```bash
python3 -m pytest \
  tests/unit_tests/server/test_server.py \
  tests/unit_tests/test_game_server_support_tracker.py \
  tests/unit_tests/gamemodules/test_common_helpers.py \
  -q
python3 scripts/generate_game_server_support_tracker.py --check
python3 -m py_compile src/server/server.py src/utils/gamemodules/common.py scripts/generate_game_server_support_tracker.py
```

Expected: PASS.

- [ ] **Step 2: Review the support totals**

Manually confirm:

- `PASSED` unchanged unless unrelated server work lands
- `ENABLED (BYO)` contains the migrated BYO modules
- `DISABLED` count drops by the migrated amount
- `docs/game-server-support.md` shows BYO-enabled modules as supported `[x]`

- [ ] **Step 3: Final commit if verification required follow-up fixes**

```bash
git add ...
git commit -m "Finalize BYO enabled-status rollout"
```
