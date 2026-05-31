# Provider Requirements API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared module API for provider-backed prerequisites, introduce public `ENABLED (AUTH)` support tracking, and migrate the first provider-backed server modules onto the shared contract.

**Architecture:** Add a new supported-status source for `ENABLED (AUTH)` beside the existing BYO source, then add a declarative `get_provider_requirements(server)` hook plus shared validation/formatting helpers in `utils.gamemodules.common`. Migrate `tiserver`, `pathoftitansserver`, `gtafivemserver`, and `redmserver` to that hook, then update tracker generation, docs, and tests to reflect the new public split.

**Tech Stack:** Python, existing AlphaGSM module hooks, Markdown docs, pytest, support-tracker generation scripts

---

## File Map

- Create: `enabled_auth_servers.conf`
  - public support-state source for provider-backed supported modules
- Create: `tests/unit_tests/gamemodules/test_provider_requirements_common.py`
  - focused coverage for new shared provider-requirement helpers
- Modify: `src/server/server.py`
  - load `ENABLED (AUTH)` rows, render create-time notice, normalize status metadata
- Modify: `src/utils/gamemodules/common.py`
  - shared provider requirement schema, validation, and formatting helpers
- Modify: `scripts/generate_game_server_support_tracker.py`
  - parse/render `ENABLED (AUTH)` as supported
- Modify: `tests/unit_tests/test_game_server_support_tracker.py`
  - support tracker coverage for the new section
- Modify: `docs/TEST_STATUS.md`
  - new summary row and section for `ENABLED (AUTH)`
- Modify: `docs/game-server-support.md`
  - regenerated after status changes
- Modify: `changelog.txt`
  - release-facing notes for the support-state split and first migrations
- Modify: `src/gamemodules/tiserver/main.py`
  - replace one-off EOS fail-fast handling with shared provider requirement metadata
- Modify: `src/gamemodules/pathoftitansserver/main.py`
  - replace Alderon auth ad hoc handling with shared provider requirement metadata
- Modify: `src/gamemodules/gtafivemserver/main.py`
  - declare Cfx provisioning/license provider requirements
- Modify: `src/gamemodules/redmserver/main.py`
  - declare Cfx provisioning/license provider requirements
- Modify: `tests/unit_tests/gamemodules/test_tiserver_cov.py`
- Modify: `tests/unit_tests/gamemodules/test_pathoftitansserver_cov.py`
- Modify: `tests/unit_tests/gamemodules/test_more_large_modules.py`
- Modify: `tests/integration_tests/test_tiserver.py`
- Modify: `tests/integration_tests/test_pathoftitansserver.py`
- Modify: `tests/integration_tests/test_gtafivemserver.py`
- Modify: `tests/integration_tests/test_redmserver.py`
- Modify: `tests/smoke_tests/run_tiserver.sh`
- Modify: `tests/smoke_tests/run_pathoftitansserver.sh`
- Modify: `tests/smoke_tests/run_gtafivemserver.sh`
- Modify: `tests/smoke_tests/run_redmserver.sh`
- Modify: `docs/servers/tiserver.md`
- Modify: `docs/servers/pathoftitansserver.md`
- Modify: `docs/servers/gtafivemserver.md`
- Modify: `docs/servers/redmserver.md`
- Modify: `enabled_byo_servers.conf`
  - remove provider-backed rows that move to `ENABLED (AUTH)`

### Task 1: Add `ENABLED (AUTH)` support-state plumbing

**Files:**
- Create: `enabled_auth_servers.conf`
- Modify: `src/server/server.py`
- Modify: `scripts/generate_game_server_support_tracker.py`
- Test: `tests/unit_tests/test_game_server_support_tracker.py`
- Test: `tests/unit_tests/server/test_server.py`

- [ ] **Step 1: Write the failing tracker/unit tests**

```python
def test_parse_status_sections_includes_enabled_auth():
    text = """
## PASSED (1)
| Test | Type |
|------|------|
| acserver | SteamCMD |

## ENABLED (AUTH) (1)
| Test | Type |
|------|------|
| tiserver | eos credentials |
"""
    rows = parse_status_sections(text)
    assert rows["ENABLED (AUTH)"] == ["tiserver"]


def test_render_support_tracker_counts_enabled_auth_as_supported():
    rows = {
        "PASSED": ["acserver"],
        "ENABLED (AUTH)": ["tiserver"],
        "ENABLED (BYO)": ["cod2server"],
        "DISABLED": [],
        "SKIPPED": [],
    }
    rendered = render_support_tracker(rows)
    assert "- [x] tiserver" in rendered
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
PYTHONPATH=.:src python3 -m pytest tests/unit_tests/test_game_server_support_tracker.py tests/unit_tests/server/test_server.py -q
```

Expected:

- failure because `ENABLED (AUTH)` is not parsed/rendered yet

- [ ] **Step 3: Add the new status source and create-time notice plumbing**

```python
_ENABLED_AUTH_SERVERS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "enabled_auth_servers.conf",
)

_ENABLED_AUTH_CATEGORY_DESCRIPTIONS = {
    "provider-auth": "provider-managed credentials or account authentication",
    "provider-token": "provider-issued runtime token",
    "provider-license": "provider-issued license or entitlement",
    "provider-provisioning": "provider-managed setup or provisioning flow",
    "mixed": "provider-managed prerequisites",
}


def _load_enabled_auth_servers():
    return _load_typed_supported_status_file(_ENABLED_AUTH_SERVERS_PATH, default_category="mixed")


def _format_enabled_auth_notice(module_name, entry):
    metadata = _normalize_supported_entry(entry, default_category="mixed")
    category_description = _ENABLED_AUTH_CATEGORY_DESCRIPTIONS.get(
        metadata["category"],
        _ENABLED_AUTH_CATEGORY_DESCRIPTIONS["mixed"],
    )
    return (
        "ENABLED (AUTH): Server module '{}' is supported, but still requires "
        "{} before setup/start can fully succeed.\nWhat to provide: {}"
    ).format(module_name, category_description, metadata["reason"])
```

- [ ] **Step 4: Update tracker generation for the new supported section**

```python
SECTIONS = (
    ("PASSED", "Supported Now", "[x]"),
    ("ENABLED (AUTH)", "Supported Now", "[x]"),
    ("ENABLED (BYO)", "Supported Now", "[x]"),
    ("DISABLED", "Not Currently Supported", "[ ]"),
    ("SKIPPED", "Waiting On Prerequisites Or Validation", "[ ]"),
)
```

- [ ] **Step 5: Add the new status file**

```text
# Enabled authenticated/provider-backed game server modules
#
# Format: module_name<TAB>category<TAB>reason
```

- [ ] **Step 6: Run focused tests to verify they pass**

Run:

```bash
PYTHONPATH=.:src python3 -m pytest tests/unit_tests/test_game_server_support_tracker.py tests/unit_tests/server/test_server.py -q
python3 scripts/generate_game_server_support_tracker.py --check
```

Expected:

- tracker tests pass
- support tracker check passes

- [ ] **Step 7: Commit**

```bash
git add enabled_auth_servers.conf src/server/server.py scripts/generate_game_server_support_tracker.py tests/unit_tests/test_game_server_support_tracker.py tests/unit_tests/server/test_server.py
git commit -m "Add ENABLED AUTH support-state plumbing"
```

### Task 2: Add shared provider requirement module helpers

**Files:**
- Modify: `src/utils/gamemodules/common.py`
- Create: `tests/unit_tests/gamemodules/test_provider_requirements_common.py`

- [ ] **Step 1: Write the failing shared-helper tests**

```python
def test_validate_provider_requirements_raises_for_missing_start_keys():
    server = DummyServer({"eos_client_id": "", "eos_client_secret": ""})
    with pytest.raises(ServerError, match="ENABLED \\(AUTH\\)"):
        common.validate_provider_requirements(
            server,
            phase="start",
            requirements=[
                {
                    "provider": "eos",
                    "kind": "credential",
                    "keys": ("eos_client_id", "eos_client_secret"),
                    "required_for": ("start",),
                    "support_category": "provider-auth",
                    "summary": "Epic Online Services dedicated-server credentials",
                    "actions": ("Set eos_client_id and eos_client_secret before starting the server",),
                    "docs_slug": "tiserver",
                }
            ],
        )


def test_validate_provider_requirements_skips_other_phases():
    server = DummyServer({"eos_client_id": "", "eos_client_secret": ""})
    common.validate_provider_requirements(
        "tiserver",
        server,
        phase="setup",
        requirements=[
            {
                "provider": "eos",
                "kind": "credential",
                "keys": ("eos_client_id", "eos_client_secret"),
                "required_for": ("start",),
                "support_category": "provider-auth",
                "summary": "Epic Online Services dedicated-server credentials",
                "actions": ("Set eos_client_id and eos_client_secret before starting the server",),
                "docs_slug": "tiserver",
            }
        ],
    )
```

- [ ] **Step 2: Run the shared-helper tests to verify they fail**

Run:

```bash
PYTHONPATH=.:src python3 -m pytest tests/unit_tests/gamemodules/test_provider_requirements_common.py -q
```

Expected:

- failure because helper functions do not exist yet

- [ ] **Step 3: Add the shared provider requirement helpers**

```python
def format_auth_support_message(module_name, requirement_summary, *, actions=(), docs_slug=None):
    message = (
        "ENABLED (AUTH): {} is supported in AlphaGSM, but this lane still requires "
        "{}.".format(module_name, requirement_summary)
    )
    normalized_actions = [str(action).strip().rstrip(".") for action in actions if str(action).strip()]
    if normalized_actions:
        message += " " + " ".join("{}.".format(action) for action in normalized_actions)
    if docs_slug:
        message += " Guide: docs/servers/{}.md.".format(docs_slug)
    return message


def validate_provider_requirements(module_name, server, *, phase, requirements):
    for requirement in requirements:
        if phase not in tuple(requirement.get("required_for", ())):
            continue
        keys = tuple(requirement.get("keys", ()))
        missing = [key for key in keys if not str(server.data.get(key, "")).strip()]
        if missing:
            raise ServerError(
                format_auth_support_message(
                    module_name,
                    requirement["summary"],
                    actions=requirement.get("actions", ()),
                    docs_slug=requirement.get("docs_slug"),
                )
            )
```

- [ ] **Step 4: Add a small shared resolver for modules**

```python
def get_provider_requirements(module, server):
    hook = getattr(module, "get_provider_requirements", None)
    if hook is None:
        return []
    return list(hook(server) or [])
```

- [ ] **Step 5: Run the helper tests to verify they pass**

Run:

```bash
PYTHONPATH=.:src python3 -m pytest tests/unit_tests/gamemodules/test_provider_requirements_common.py -q
```

Expected:

- provider helper tests pass

- [ ] **Step 6: Commit**

```bash
git add src/utils/gamemodules/common.py tests/unit_tests/gamemodules/test_provider_requirements_common.py
git commit -m "Add shared provider requirement helpers"
```

### Task 3: Migrate `tiserver` and `pathoftitansserver` to the shared API

**Files:**
- Modify: `src/gamemodules/tiserver/main.py`
- Modify: `src/gamemodules/pathoftitansserver/main.py`
- Modify: `tests/unit_tests/gamemodules/test_tiserver_cov.py`
- Modify: `tests/unit_tests/gamemodules/test_pathoftitansserver_cov.py`
- Modify: `tests/unit_tests/gamemodules/test_more_large_modules.py`
- Modify: `tests/integration_tests/test_tiserver.py`
- Modify: `tests/integration_tests/test_pathoftitansserver.py`
- Modify: `tests/smoke_tests/run_tiserver.sh`
- Modify: `tests/smoke_tests/run_pathoftitansserver.sh`
- Modify: `docs/servers/tiserver.md`
- Modify: `docs/servers/pathoftitansserver.md`

- [ ] **Step 1: Write/adjust failing module tests for shared provider metadata**

```python
def test_tiserver_provider_requirements():
    server = DummyServer()
    requirements = mod.get_provider_requirements(server)
    assert requirements == [
        {
            "provider": "eos",
            "kind": "credential",
            "keys": ("eos_client_id", "eos_client_secret"),
            "required_for": ("start",),
            "support_category": "provider-auth",
            "summary": "Epic Online Services dedicated-server credentials",
            "actions": (
                "Set eos_client_id and eos_client_secret before starting the server",
            ),
            "docs_slug": "tiserver",
        }
    ]
```

- [ ] **Step 2: Run the module tests to verify they fail**

Run:

```bash
PYTHONPATH=.:src python3 -m pytest tests/unit_tests/gamemodules/test_tiserver_cov.py tests/unit_tests/gamemodules/test_pathoftitansserver_cov.py tests/unit_tests/gamemodules/test_more_large_modules.py -q -k 'tiserver or pathoftitansserver'
```

Expected:

- failure because `get_provider_requirements` does not exist on those modules yet

- [ ] **Step 3: Refactor `tiserver` to declare provider requirements and call the shared validator**

```python
def get_provider_requirements(server):
    return [
        {
            "provider": "eos",
            "kind": "credential",
            "keys": ("eos_client_id", "eos_client_secret"),
            "required_for": ("start",),
            "support_category": "provider-auth",
            "summary": "Epic Online Services dedicated-server credentials",
            "actions": (
                "Set eos_client_id and eos_client_secret before starting the server",
                "Use the official dedicated-server guide to create TheIsle/Saved/Config/LinuxServer/Engine.ini if you prefer file-based EOS configuration",
            ),
            "docs_slug": "tiserver",
        }
    ]


def get_start_command(server):
    ...
    gamemodule_common.validate_provider_requirements(
        server,
        phase="start",
        requirements=get_provider_requirements(server),
    )
```

- [ ] **Step 4: Refactor `pathoftitansserver` to use the same shared provider hook**

```python
def get_provider_requirements(server):
    return [
        {
            "provider": "alderon",
            "kind": "token",
            "keys": ("auth_token",),
            "required_for": ("setup",),
            "support_category": "provider-token",
            "summary": "an Alderon host account auth token or staged archive override",
            "actions": (
                "Set auth_token to an Alderon host account token before rerunning setup, or set url to a direct staged archive override",
                "Retry setup once the token or staged archive path is available",
            ),
            "docs_slug": "pathoftitansserver",
        }
    ]
```

- [ ] **Step 5: Update integration/smoke/docs wording to `ENABLED (AUTH)`**

```python
@pytest.mark.skip(
    reason="ENABLED (AUTH): set auth_token to an Alderon host account token or provide a staged archive override before setup/start"
)
```

```bash
echo "Smoke test for tiserver requires eos_client_id and eos_client_secret - see docs/servers/tiserver.md"
```

- [ ] **Step 6: Run focused tests to verify they pass**

Run:

```bash
PYTHONPATH=.:src python3 -m pytest tests/unit_tests/gamemodules/test_tiserver_cov.py tests/unit_tests/gamemodules/test_pathoftitansserver_cov.py tests/unit_tests/gamemodules/test_more_large_modules.py -q -k 'tiserver or pathoftitansserver'
python3 -m py_compile src/gamemodules/tiserver/main.py src/gamemodules/pathoftitansserver/main.py tests/integration_tests/test_tiserver.py tests/integration_tests/test_pathoftitansserver.py
bash -n tests/smoke_tests/run_tiserver.sh tests/smoke_tests/run_pathoftitansserver.sh
```

Expected:

- focused unit tests pass
- py_compile passes
- shell syntax checks pass

- [ ] **Step 7: Commit**

```bash
git add src/gamemodules/tiserver/main.py src/gamemodules/pathoftitansserver/main.py tests/unit_tests/gamemodules/test_tiserver_cov.py tests/unit_tests/gamemodules/test_pathoftitansserver_cov.py tests/unit_tests/gamemodules/test_more_large_modules.py tests/integration_tests/test_tiserver.py tests/integration_tests/test_pathoftitansserver.py tests/smoke_tests/run_tiserver.sh tests/smoke_tests/run_pathoftitansserver.sh docs/servers/tiserver.md docs/servers/pathoftitansserver.md
git commit -m "Migrate EOS and Alderon modules to provider API"
```

### Task 4: Migrate `gtafivemserver` and `redmserver`

**Files:**
- Modify: `src/gamemodules/gtafivemserver/main.py`
- Modify: `src/gamemodules/redmserver/main.py`
- Modify: `tests/integration_tests/test_gtafivemserver.py`
- Modify: `tests/integration_tests/test_redmserver.py`
- Modify: `tests/smoke_tests/run_gtafivemserver.sh`
- Modify: `tests/smoke_tests/run_redmserver.sh`
- Modify: `docs/servers/gtafivemserver.md`
- Modify: `docs/servers/redmserver.md`
- Test: add/update focused unit coverage file(s) already covering these modules

- [ ] **Step 1: Write the failing provider-requirement tests for Cfx-backed modules**

```python
def test_gtafivemserver_provider_requirements():
    requirements = mod.get_provider_requirements(DummyServer())
    assert requirements[0]["provider"] == "cfx"
    assert requirements[0]["kind"] == "provisioning"
    assert "server.cfg" in requirements[0]["summary"]
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
PYTHONPATH=.:src python3 -m pytest tests/unit_tests/gamemodules -q -k 'gtafivemserver or redmserver'
```

Expected:

- failure because provider requirement hooks are not declared yet

- [ ] **Step 3: Add provider requirement metadata to both Cfx modules**

```python
def get_provider_requirements(server):
    return [
        {
            "provider": "cfx",
            "kind": "provisioning",
            "keys": (),
            "required_for": ("start",),
            "support_category": "provider-provisioning",
            "summary": "txAdmin or vanilla server-data provisioning plus a Cfx license key",
            "actions": (
                "Complete txAdmin/server-data provisioning with server.cfg and a Cfx license key before lifecycle validation",
            ),
            "docs_slug": "gtafivemserver",
        }
    ]
```

- [ ] **Step 4: Update docs/integration/smoke wording to `ENABLED (AUTH)`**

```python
@pytest.mark.skip(
    reason="ENABLED (AUTH): complete txAdmin/server-data provisioning with server.cfg and a Cfx license key before lifecycle validation"
)
```

- [ ] **Step 5: Run focused verification**

Run:

```bash
PYTHONPATH=.:src python3 -m pytest tests/unit_tests/gamemodules -q -k 'gtafivemserver or redmserver'
python3 -m py_compile src/gamemodules/gtafivemserver/main.py src/gamemodules/redmserver/main.py tests/integration_tests/test_gtafivemserver.py tests/integration_tests/test_redmserver.py
bash -n tests/smoke_tests/run_gtafivemserver.sh tests/smoke_tests/run_redmserver.sh
```

Expected:

- focused unit tests pass
- py_compile passes
- shell syntax checks pass

- [ ] **Step 6: Commit**

```bash
git add src/gamemodules/gtafivemserver/main.py src/gamemodules/redmserver/main.py tests/integration_tests/test_gtafivemserver.py tests/integration_tests/test_redmserver.py tests/smoke_tests/run_gtafivemserver.sh tests/smoke_tests/run_redmserver.sh docs/servers/gtafivemserver.md docs/servers/redmserver.md
git commit -m "Migrate Cfx modules to provider API"
```

### Task 5: Reclassify support rows and regenerate published docs

**Files:**
- Modify: `enabled_byo_servers.conf`
- Modify: `enabled_auth_servers.conf`
- Modify: `docs/TEST_STATUS.md`
- Modify: `docs/game-server-support.md`
- Modify: `changelog.txt`

- [ ] **Step 1: Move provider-backed rows out of BYO and into AUTH**

```text
# enabled_auth_servers.conf
tiserver	provider-auth	set eos_client_id and eos_client_secret for Epic Online Services dedicated-server authentication before start
pathoftitansserver	provider-token	set auth_token to an Alderon host account token or provide a staged archive override before setup/start
gtafivemserver	provider-provisioning	complete txAdmin/server-data provisioning with server.cfg and a Cfx license key before lifecycle validation
redmserver	provider-provisioning	complete txAdmin/server-data provisioning with server.cfg and a Cfx license key before lifecycle validation
```

- [ ] **Step 2: Update the public tracker section headers and counts**

```markdown
| PASSED | 129 |
| ENABLED (AUTH) | 4 |
| ENABLED (BYO) | 28 |
| DISABLED | ... |
| SKIPPED | ... |
```

```markdown
## ENABLED (AUTH) (4)
| Test | Type |
|------|------|
| tiserver | EOS dedicated-server client ID/secret for Epic Online Services authentication |
| pathoftitansserver | Alderon auth token or staged archive override/server tree |
| gtafivemserver | txAdmin/server-data provisioning plus Cfx license key |
| redmserver | txAdmin/server-data provisioning plus Cfx license key |
```

- [ ] **Step 3: Add the release note**

```markdown
- Support state/provider API: split provider-backed supported modules into public `ENABLED (AUTH)` rows, keep true operator-supplied asset/export/url/service lanes under `ENABLED (BYO)`, and migrate the first EOS/Alderon/Cfx-backed modules onto the shared provider-requirements hook.
```

- [ ] **Step 4: Regenerate and verify published support docs**

Run:

```bash
python3 scripts/generate_game_server_support_tracker.py
python3 scripts/generate_game_server_support_tracker.py --check
```

Expected:

- `docs/game-server-support.md` regenerates cleanly
- `--check` returns success

- [ ] **Step 5: Commit**

```bash
git add enabled_byo_servers.conf enabled_auth_servers.conf docs/TEST_STATUS.md docs/game-server-support.md changelog.txt
git commit -m "Publish ENABLED AUTH support-state split"
```

### Task 6: Final verification and publish

**Files:**
- Modify: none expected
- Test: focused unit tracker/module coverage from previous tasks

- [ ] **Step 1: Run the final focused verification batch**

Run:

```bash
PYTHONPATH=.:src python3 -m pytest \
  tests/unit_tests/test_game_server_support_tracker.py \
  tests/unit_tests/server/test_server.py \
  tests/unit_tests/gamemodules/test_provider_requirements_common.py \
  tests/unit_tests/gamemodules/test_tiserver_cov.py \
  tests/unit_tests/gamemodules/test_pathoftitansserver_cov.py \
  tests/unit_tests/gamemodules/test_more_large_modules.py \
  -q
python3 -m py_compile \
  src/server/server.py \
  src/utils/gamemodules/common.py \
  src/gamemodules/tiserver/main.py \
  src/gamemodules/pathoftitansserver/main.py \
  src/gamemodules/gtafivemserver/main.py \
  src/gamemodules/redmserver/main.py
python3 scripts/generate_game_server_support_tracker.py --check
```

Expected:

- all focused tests pass
- py_compile passes
- support tracker check passes

- [ ] **Step 2: Review staged diff before publish**

Run:

```bash
git status --short
git diff --stat origin/release_v1..HEAD
```

Expected:

- only provider API / support-state files are part of this slice

- [ ] **Step 3: Push the branch**

```bash
git push -u origin release_v1
```

- [ ] **Step 4: Check PR health**

Run:

```bash
gh pr checks 36
```

Expected:

- top-level checks start on the new head

## Self-Review

- Spec coverage:
  - shared provider module API: covered in Task 2
  - public `ENABLED (AUTH)` support state: covered in Tasks 1 and 5
  - first migrations (`tiserver`, `pathoftitansserver`, `gtafivemserver`, `redmserver`): covered in Tasks 3 and 4
  - future SteamCMD auth compatibility: addressed by the shared hook shape introduced in Task 2
- Placeholder scan:
  - no `TBD` / `TODO` placeholders remain in tasks
- Type consistency:
  - plan consistently uses `get_provider_requirements(server)`
  - support categories consistently use `provider-auth`, `provider-token`, `provider-license`, `provider-provisioning`
  - public state consistently uses `ENABLED (AUTH)`
