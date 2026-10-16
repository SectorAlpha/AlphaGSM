# BYO Helper Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Correct three reproduced mismatches between BYO file helpers and existing game-module file contracts, without requiring Steam credentials.

**Architecture:** Keep source selection flexible while checking installed paths with native filesystem semantics. Extend archive-member requirements to express equivalent map formats, and separate external configuration homes from portable import-relative paths. Retain transactional publication and private SteamCMD sessions.

**Tech Stack:** Python 3.10+, pathlib, zipfile, pytest, existing AlphaGSM asset recipes and CLI.

---

## Scope and evidence

Review date: 2026-10-16. Reviewed commit `9412263b` against parent `2e26dd28` on `codex/byo-file-helpers`.

Worktree: `/home/cosmosquark/.codex/worktrees/byo-file-helpers/AlphaGSM`. All paths below are relative to this worktree. Preserve unrelated Reclaimer changes in the original checkout.

This plan was written during a read-only review. Execution is complete; verified results are recorded below.

| Priority | Location in reviewed commit | Reproduced result |
| --- | --- | --- |
| P2 | `src/utils/byo_files.py:147` | With only `BaseQ3/PAK0.PK3`, the helper reports files ready, but the Linux Q3 lifecycle requires `baseq3/pak0.pk3` and rejects the same tree. |
| P2 | `src/gamemodules/codserver/byo_assets.json:5-7` and `src/utils/byo_files.py:97-103` | PK3 maps named `maps/mp/mp_carentan.d3dbsp` or `MAPS/MP/MP_CARENTAN.BSP` pass `codserver.has_start_map`, but fail the helper. Import also rejects the valid selected content. |
| P2 | `src/utils/byo_files.py:49-52` | ETS2 and ATS accept absolute `configdir` values and use them as their native homes. The requirements hook instead raises `Unsafe BYO requirement path`, preventing requirements/check even when both exported files exist. |

The Q3 mismatch is a file-contract false positive; it does not depend on claiming game readiness. The CoD finding concerns archive formats already accepted by the module. Keep base-game acquisition rooted in `main/`; changes to mod acquisition are outside this fix plan.

Fresh authentication review found no additional actionable defect. Real cached-session behavior, account entitlement, and Steam-created files remain unverified until an operator performs a live test.

### Verification performed during review

- 91 focused unit tests passed on the host filesystem, including fake-process authentication, BYO inspection, acquisition, import selection, and command parsing.
- Independent BYO review also passed 82 focused tests including existing import/export tests.
- Small temporary-file reproductions confirmed all three findings independently of those passing tests.
- The sandbox remaps ownership of `/` to UID 65534, so the initial sandboxed authentication run failed the ancestor-owner guard before reaching its cases. The unchanged suite passed outside that remapping; do not weaken security checks to accommodate the sandbox.
- No Steam login, Steam bootstrap, game download, or live server process was run. CI integration testing remains deferred at the user's request.

## File responsibilities

- `src/utils/byo_files.py`: installed/source inspection modes, archive-member alternatives, external-home recipe preparation.
- `src/utils/byo_acquire.py`: explicitly select source inspection for temporary downloads.
- `src/gamemodules/codserver/byo_assets.json`: equivalent PK3 map-member formats.
- `src/gamemodules/ets2server/byo_assets.json`, `src/gamemodules/atsserver/byo_assets.json`: opt in to external configuration-home handling.
- `tests/unit_tests/utils/test_byo_files.py`: file-contract regressions.
- `tests/unit_tests/utils/test_byo_selection_validation.py`: import/export still enforce the richer contract.
- `tests/unit_tests/utils/test_byo_acquire.py`: mixed-case source download remains importable and is normalized before publication.
- `tests/unit_tests/server/test_byo_asset_commands.py`: external-home requirements/check routing and guarded mutations.
- `docs/byo-files.md`, matching three server guides, `DEVELOPERS.md`, `changelog.txt`: explain the resulting behavior and remaining validation limits.

## Task 1: Separate installed checks from source matching

- [x] Add this failing regression to `tests/unit_tests/utils/test_byo_files.py`:

```python
def test_q3_installed_check_requires_native_destination_case(tmp_path):
    from gamemodules import q3server
    from types import SimpleNamespace
    from utils import byo_files

    (tmp_path / 'BaseQ3').mkdir()
    (tmp_path / 'BaseQ3/PAK0.PK3').write_bytes(b'owned')
    recipe = q3server.get_asset_requirements(SimpleNamespace(name='q3', data={}))
    assert not byo_files.inspect_files(tmp_path, recipe)['ready']
```

Run on Linux. Expected before fix: assertion fails because `ready` is True.

- [x] Change `inspect_files` to take a keyword-only source mode. Keep existing return fields and missing-file behavior. Use this matching policy inside its requirement loop:

```python
def inspect_files(root, recipe, *, source=False):
    """Report declared file availability and sources, never game readiness."""
    root = Path(root).absolute() if root else None
    missing, optional = [], []
    requirements = recipe.get('requirements', [])
    if not isinstance(requirements, list) or not requirements:
        raise ServerError('This recipe does not declare BYO file requirements')
    insensitive = bool(recipe.get('case_insensitive', False)) if source else False
    for requirement in requirements:
        if not _satisfied(root, requirement, insensitive):
            label = requirement.get('path') or ' or '.join(requirement['any_of'])
            (optional if requirement.get('optional') else missing).append(label)
    return {'status': 'missing' if missing else 'ready', 'ready': not missing,
            'missing': missing, 'optional_missing': optional,
            'requirements': deepcopy(requirements),
            'sources': deepcopy(recipe.get('sources', [])),
            'validation': recipe.get('validation', 'declared-files'),
            'managed_import': recipe.get('managed_import', False),
            'game_readiness': 'not-checked'}
```

`False` here uses native `Path.glob` behavior; Linux requires exact spelling. Do not change `_select`'s source normalization or remove `destination_names`.

- [x] Change the acquisition precheck in `src/utils/byo_acquire.py` to:

```python
inspection = byo_files.inspect_files(scratch, recipe, source=True)
```

Leave `server.assets check` and `validate_staged_files` on the default installed mode. Selected staged files already have their canonical destination names.

- [x] Add source/destination regression coverage, using the Q3 recipe above:

```python
def test_q3_case_flexible_source_is_published_canonically(tmp_path):
    from gamemodules import q3server
    from types import SimpleNamespace
    from utils import asset_import, byo_files

    source = tmp_path / 'owned'
    (source / 'BaseQ3').mkdir(parents=True)
    (source / 'BaseQ3/PAK0.PK3').write_bytes(b'owned')
    target = tmp_path / 'server'
    recipe = q3server.get_asset_requirements(SimpleNamespace(name='q3', data={}))
    assert byo_files.inspect_files(source, recipe, source=True)['ready']
    asset_import.import_assets(source, target, recipe)
    assert (target / 'baseq3/pak0.pk3').read_bytes() == b'owned'
    assert byo_files.inspect_files(target, recipe)['ready']
    q3server._assert_required_base_assets(str(target))
```

In `test_byo_acquire.py`, repeat its existing successful acquisition fixture with fake download paths `BaseQ3/PAK0.PK3`; assert canonical target paths and staging cleanup. Run the affected tests and confirm both ordinary and mixed-case fake downloads pass.

- [x] Commit this self-contained fix after the regression tests pass.

## Task 2: Express equivalent CoD archive map formats

- [x] Add parameterized regressions in `test_byo_selection_validation.py` that create one PK3 containing each member below, assert `codserver.has_start_map` accepts it, import/export it, then verify the installed declaration succeeds:

```python
@pytest.mark.parametrize('member', [
    'maps/mp/mp_carentan.bsp',
    'maps/mp/mp_carentan.d3dbsp',
    'MAPS/MP/MP_CARENTAN.BSP',
    'maps\\mp\\mp_carentan.d3dbsp',
])
def test_cod_equivalent_archive_members_round_trip(tmp_path, member):
    from zipfile import ZipFile
    from types import SimpleNamespace
    from gamemodules import codserver
    from utils import asset_import, byo_files

    source = tmp_path / 'owned'
    (source / 'main').mkdir(parents=True)
    with ZipFile(source / 'main/map.pk3', 'w') as bundle:
        bundle.writestr(member, b'map')
    recipe = codserver.get_asset_requirements(SimpleNamespace(name='cod', data={}))
    assert codserver.has_start_map(source, 'mp_carentan')
    target = tmp_path / 'server'
    asset_import.import_assets(source, target, recipe)
    assert byo_files.inspect_files(target, recipe)['ready']
    asset_import.export_assets(source, tmp_path / 'maps.zip', recipe)
```

Expected before fix: non-lowercase-BSP variants fail. Retain existing wrong-map and invalid-ZIP rejection tests.

- [x] Replace CoD's single `member` declaration with:

```json
"member_any_of": [
  "maps/mp/{startmap}.bsp",
  "maps/mp/{startmap}.d3dbsp"
],
"member_case_insensitive": true
```

Keep `path: main/*.pk3` and its allowlist. Archive member case policy is separate from filesystem path case policy.

- [x] In `load_requirements`, expand `member_any_of` exactly as `any_of` is expanded. Reject an empty member-alternative group in `_satisfied`; run every member pattern through `relative_path` before opening archives. Keep old `member` recipes compatible.

Use this archive inspection implementation and update its caller to pass `members` and the explicit archive case flag:

```python
def _archive_contains(path, members, *, insensitive=False):
    def canonical(value):
        value = value.replace('\\', '/')
        while value.startswith('./'):
            value = value[2:]
        return value.casefold() if insensitive else value

    patterns = [canonical(member) for member in members]
    try:
        with zipfile.ZipFile(path) as bundle:
            return any(
                info.file_size > 0 and not info.is_dir()
                and any(fnmatch.fnmatchcase(canonical(info.filename), pattern)
                        for pattern in patterns)
                for info in bundle.infolist()
            )
    except (OSError, ValueError, zipfile.BadZipFile):
        return False
```

Inside `_satisfied`, when kind is `archive-member`, compute:

```python
members = requirement.get('member_any_of')
if members is None:
    members = [requirement.get('member', '')]
if not isinstance(members, list) or not members:
    raise ServerError('BYO archive member alternatives cannot be empty')
for member in members:
    relative_path(member)
```

Use `_archive_contains(path, members, insensitive=requirement.get('member_case_insensitive', False))`. Do not translate member paths by the filesystem publication target in `validate_staged_files`.

- [x] Run both new round-trip regressions and existing invalid/irrelevant-map tests. Verify a PK3 containing another multiplayer map still fails before any target or ZIP is published.

- [x] Commit this fix independently.

## Task 3: Inspect absolute truck-server configuration homes safely

Choose the narrow behavior: requirements/check work for absolute configuration homes; managed import/export into those homes is explicitly unavailable and explains manual staging. Relative configuration homes retain their current import destination and ownership manifest layout. This avoids silently broadening the importer's write authority or moving existing ownership records.

- [x] Add a parameterized regression to `test_byo_files.py`:

```python
@pytest.mark.parametrize('module_id', ['ets2server', 'atsserver'])
def test_absolute_export_home_is_inspectable(tmp_path, module_id):
    from importlib import import_module
    from types import SimpleNamespace
    from utils import byo_files

    module = import_module('gamemodules.' + module_id)
    home = tmp_path / 'external-exports'
    home.mkdir()
    for filename in ('server_packages.sii', 'server_packages.dat'):
        (home / filename).write_bytes(b'client export')
    server = SimpleNamespace(name='truck', data={
        'dir': str(tmp_path / 'server'), 'configdir': str(home)})
    assert module._server_home_dir(server) == str(home)
    recipe = module.get_asset_requirements(server)
    assert recipe['managed_import'] is False
    assert byo_files.inspection_root(server, recipe) == str(home)
    assert byo_files.inspect_files(home, recipe)['ready']
```

Expected before fix: requirements loading raises `Unsafe BYO requirement path`.

- [x] Add `"config_home_setting": "configdir"` to the ETS2 and ATS manifests. Prepare their external-root form after JSON loading and before template expansion in `load_requirements`. Add this helper and call `_prepare_external_home(server, recipe)` before building template values:

```python
def _prepare_external_home(server, recipe):
    key = recipe.get('config_home_setting')
    if key is None:
        return
    if key not in {'configdir', 'confdir'}:
        raise ServerError('Invalid BYO configuration home setting')
    home = server.data.get(key, recipe.get('defaults', {}).get(key, ''))
    if not os.path.isabs(str(home)):
        return
    prefix = '{' + key + '}/'
    for item in recipe['requirements']:
        fields = ('path',) if 'path' in item else ('any_of',)
        for field in fields:
            paths = [item[field]] if field == 'path' else item[field]
            if any(not path.startswith(prefix) for path in paths):
                raise ServerError('Configuration-home requirements must be relative to that home')
            paths = [relative_path(path[len(prefix):]) for path in paths]
            item[field] = paths[0] if field == 'path' else paths
    recipe.update(
        root_setting=key,
        target='',
        managed_import=False,
        manual_reason=(
            'An absolute configuration home requires manual staging. '
            'Copy server_packages.sii and server_packages.dat into the configured '
            'home, then run assets check.'
        ),
    )
```

Absolute values remain roots, never relative recipe paths. Do not loosen `relative_path`, follow symlinks, or pass an absolute target to the importer. This helper only changes opted-in manifests.

- [x] In `test_byo_asset_commands.py`, parameterize both truck modules using `Server.__new__` as the existing tests do. Run `server.assets('requirements', as_json=True)` and `server.assets('check', as_json=True)` with a complete absolute home; parse the JSON and assert success. Stub the stopped runtime and assert both import and export raise the manual-staging error without touching either external files or the installation directory.

- [x] Retain the existing relative `custom-home` test, and add an import of both exports into a relative custom home to prove target placement and `.alphagsm/assets.json` stay under the installation root. Keep unsafe declared absolute-path tests green.

- [x] Commit this fix independently.

## Task 4: Documentation and final verification

- [x] Read `skills/changelog-discipline/SKILL.md`. Add one changelog entry covering the three corrected file-helper behaviors. No smoke runner change is needed because these fixes neither change server launch commands nor establish live lifecycle support.
- [x] Update `docs/byo-files.md` and `DEVELOPERS.md`: explain source versus installed path matching, `member_any_of`/`member_case_insensitive`, and manual staging for absolute configuration homes. Update `docs/servers/codserver.md`, `docs/servers/ets2server.md`, and `docs/servers/atsserver.md` with their relevant corrected behavior. Keep the existing Steam authentication and CI deferral limitations explicit. No support-state promotion is justified by these offline regressions.
- [x] Run the focused suite from this worktree:

```bash
PYTHONDONTWRITEBYTECODE=1 /tmp/alphagsm-agent-venv/bin/python -m pytest -q -p no:cacheprovider tests/unit_tests/utils/test_steam_auth.py tests/unit_tests/core/test_steam_auth.py tests/unit_tests/utils/test_byo_files.py tests/unit_tests/utils/test_byo_acquire.py tests/unit_tests/utils/test_byo_import_patterns.py tests/unit_tests/utils/test_byo_selection_validation.py tests/unit_tests/server/test_byo_asset_commands.py --basetemp=/tmp/alphagsm-byo-fixes-tests
```

Expected: all tests pass, including the added regression cases. In this desktop environment, authentication ownership tests require the real host filesystem rather than the sandbox's remapped root ownership. Request the normal execution override; do not alter product security checks for the test environment.

- [x] Run the repository gates once after all implementation and documentation changes:

```bash
PYTEST_XDIST_AUTO_NUM_WORKERS=4 make test PYTHON_BIN=/tmp/alphagsm-agent-venv/bin/python
make lint PYTHON_BIN=/tmp/alphagsm-agent-venv/bin/python
```

Expected: unit suite green and pylint `10.00/10`. Use the existing test environment because the default interpreter has an incompatible `crontab` package. No CI credential integration test is required for this fix campaign.

- [x] Review the final diff for unintended runtime, ownership, provider, or support-state changes. Record actual test counts and remaining live-validation limits, then commit the documentation with the completed fix series.

## Later operator-assisted validation

When the user is ready, choose one owned game and use the existing `.local-tests/README.md` handoff in this worktree. Keep Steam interaction local and interactive. Check requirements, log into the private profile, fetch the declared source, check canonical installed files, then validate the selected game's normal setup/start/readiness/query/info/stop flow only within the user's authorized local scope. No current task depends on credentials or this live validation.


## Execution record — completed 2026-10-16

- Task 1: `358e8b1c` separates source and installed path matching. Regression tests first reproduced the incorrect installed/staged acceptance; 76 relevant offline tests passed after the fix.
- Task 2: `b3dba968` supports equivalent CoD archive member formats. The red run had 20 expected failures; the broader relevant suite passed 129 tests afterward.
- Task 3: `698142ed` inspects absolute ETS2/ATS homes without managed writes. The red run had 16 expected failures; 204 focused BYO/auth tests passed afterward.
- Each task passed separate spec and code-quality reviews. A final combined review of all fixes and documentation found no further actionable issue.
- Final repository gate: `PYTEST_XDIST_AUTO_NUM_WORKERS=4 make test PYTHON_BIN=/tmp/alphagsm-agent-venv/bin/python` passed with **10057 passed, 4 skipped in 186.57 seconds**. Log: `/tmp/alphagsm-byo-fixes-unit.log`.
- Final lint gate: `make lint PYTHON_BIN=/tmp/alphagsm-agent-venv/bin/python` validated 35 skills and scored **10.00/10**. Log: `/tmp/alphagsm-byo-fixes-lint.log`.
- Changelog, the three affected server guides, shared BYO guide, and developer documentation are updated. No launch/smoke workflow or public support state changed.
- No Steam login, bootstrap, real game download, or live server test was run. Authenticated CI integration remains deferred at the user's request. The branch and local-test handoff are preserved for later operator-assisted validation.
