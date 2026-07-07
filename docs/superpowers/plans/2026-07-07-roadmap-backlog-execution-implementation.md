# Roadmap Backlog Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the remaining non-future items from `docs/improvement-roadmap.md` in the right order: stabilize active CI first, close the remaining runtime-contract gaps second, then work through the support-state backlog with unit-test-first changes and CI-only integration validation.

**Architecture:** Treat the roadmap as four workstreams instead of one giant branch: roadmap reconciliation, CI stabilization, runtime-contract closure, and support-state backlog follow-up. Use subagents only for independent investigations, add or extend unit/static tests before implementation changes where practical, and let GitHub CI remain the only place full integration and smoke validation runs.

**Tech Stack:** Python, pytest, GitHub CLI, GitHub Actions YAML, Markdown docs, AlphaGSM integration harness, existing module coverage tests

---

## File Map

- Modify: `docs/improvement-roadmap.md`
  - reconcile which non-future items are done, in progress, still open, or now blocked by a known red gate
- Modify: `docs/superpowers/specs/2026-07-07-roadmap-backlog-execution-design.md`
  - only if design constraints must be clarified during execution
- Create: `docs/superpowers/plans/2026-07-07-roadmap-backlog-execution-implementation.md`
  - this execution plan
- Modify: `.github/workflows/unittest.yaml`
  - only if CI stabilization identifies a workflow-level root cause
- Modify: `tests/integration_tests/conftest.py`
  - shared integration harness fixes, diagnostics, runtime selection, or redaction improvements
- Modify: `tests/unit_tests/test_ci_game_test_routing.py`
  - static coverage for workflow/routing behavior when CI or matrix logic changes
- Modify: `tests/unit_tests/test_integration_conftest_helpers.py`
  - unit coverage for shared integration helper fixes
- Create: `tests/unit_tests/test_integration_runtime_policy.py`
  - focused unit/static coverage if runtime-lane selection logic needs shared tests
- Modify: `tests/unit_tests/test_runtime_contract_static.py`
  - static coverage for Docker/process runtime command or contract fixes
- Modify: `tests/integration_tests/test_btserver.py`
  - A2S contract resolution if `btserver` remains part of the runtime gap
- Modify: `tests/integration_tests/test_valheim.py`
  - A2S contract resolution if `valheim` remains part of the runtime gap
- Modify: `tests/smoke_tests/run_btserver.sh`
- Modify: `tests/smoke_tests/run_valheim.sh`
  - smoke alignment if the runtime/query contract changes
- Modify: `tests/unit_tests/gamemodules/helpers.py`
  - opportunistic reuse only when touched module coverage suites need it
- Modify: `docs/TEST_STATUS.md`
  - support-state promotions or re-verification notes
- Modify: `enabled_byo_servers.conf`
- Modify: `disabled_servers.conf`
  - support-state source-of-truth updates
- Modify: `docs/servers/abfserver.md`
- Modify: `docs/servers/bobserver.md`
- Modify: `docs/servers/counterstrikeglobaloffensive.md`
  - current exact server guides already known to be in the non-future disabled re-verification set
- Modify: `changelog.txt`
  - release-facing notes for CI/runtime/support-state changes

## Task 1: Reconcile The Roadmap With Current Repo State

**Files:**
- Modify: `docs/improvement-roadmap.md`
- Modify: `changelog.txt`

- [ ] **Step 1: Identify stale or already-completed roadmap references**

Run:

```bash
rg -n "Done:|pick-up order|deduplicate|executable resolver|runtime-image resolvers|queue|queued|btserver|valheim" docs/improvement-roadmap.md changelog.txt
```

Expected:

- evidence for items that are already done but still mentioned as future pick-up work
- evidence for newly completed queue/concurrency work that should be reflected in the roadmap

- [ ] **Step 2: Update the roadmap status prose before touching more code**

Edit `docs/improvement-roadmap.md` so it reflects the current repo truth with prose shaped like:

```markdown
- `AlphaGSM PR` now cancels superseded pull-request runs, so queued workflow
  pile-ups are no longer an open infrastructure item.
- The active open work is the broad red smoke/integration set on `release_v1`;
  treat that as the top-priority CI stabilization item before more enablement
  work.
- Earlier “pick-up order” references to runtime-image resolver dedupe and the
  shared executable resolver are now historical context only; those tasks are
  complete.
```

- [ ] **Step 3: Re-read the updated roadmap for internal consistency**

Run:

```bash
sed -n '1,220p' docs/improvement-roadmap.md
sed -n '480,520p' docs/improvement-roadmap.md
```

Expected:

- the “Current State”, open-item sections, and “Suggested Pick-Up Order” no longer contradict each other

- [ ] **Step 4: Commit the roadmap reconciliation**

```bash
git add docs/improvement-roadmap.md changelog.txt
git commit -m "docs: reconcile roadmap backlog status"
```

## Task 2: Classify The Active Red CI Gates Before Fixing Anything

**Files:**
- Modify: `docs/improvement-roadmap.md`
- Modify: `changelog.txt`
- Modify: `tests/integration_tests/conftest.py`
- Modify: `tests/unit_tests/test_integration_conftest_helpers.py`
- Modify: `.github/workflows/unittest.yaml`
- Modify: `tests/unit_tests/test_ci_game_test_routing.py`

- [ ] **Step 1: Capture the latest failing lanes from GitHub without running integration locally**

Run:

```bash
gh pr checks 36
gh run list --workflow "AlphaGSM PR" --limit 3 --json databaseId,status,conclusion,headSha,createdAt,updatedAt,displayTitle
```

Expected:

- a current set of red `smoke-test` / `integration-test` jobs on the newest `release_v1` head
- no need to run `tests/integration_tests/*` locally

- [ ] **Step 2: Dispatch parallel subagents for 2-3 representative failed lanes**

Each subagent should get one job id and must return:

```text
1. failing server/test names
2. shared helper vs module-specific vs infra classification
3. suspected root cause
4. exact files likely involved if the failure is shared
```

Use representative job groups:

- one failing smoke batch
- one failing standard integration batch
- one failing `slow-*` integration lane

- [ ] **Step 3: Convert any shared root cause into a unit/static test first**

If the shared cause lands in the integration harness or workflow logic, add a focused test before implementation in one of:

```python
def test_runtime_doctor_output_includes_expected_context():
    rendered = format_runtime_doctor(
        backend="docker",
        module_runtime_preference="docker",
        command=["./start.sh"],
        mounts=["/srv/server:/home/gsmuser/server"],
        published_ports=["2456:2456/udp"],
    )
    assert "Configured backend: docker" in rendered
    assert "Module runtime preference: docker" in rendered
    assert "./start.sh" in rendered
```

```python
def test_pr_workflow_cancels_superseded_runs():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "concurrency:" in text
    assert "cancel-in-progress: true" in text
```

- [ ] **Step 4: Implement the smallest shared fix and verify locally with unit/static tests only**

Run the narrowest relevant commands, for example:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/cosmosquark/.pyenv/versions/alphagsm/bin/python -m pytest -q tests/unit_tests/test_integration_conftest_helpers.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/cosmosquark/.pyenv/versions/alphagsm/bin/python -m pytest -q tests/unit_tests/test_ci_game_test_routing.py -k workflow
```

Expected:

- focused green unit/static coverage for the shared fix

- [ ] **Step 5: Push and let GitHub CI re-run the integration/smoke surface**

```bash
git add .github/workflows/unittest.yaml tests/integration_tests/conftest.py tests/unit_tests/test_integration_conftest_helpers.py tests/unit_tests/test_ci_game_test_routing.py changelog.txt
git commit -m "ci: fix shared integration backlog regression"
git push -u origin release_v1
gh pr checks 36 --watch --interval 10
```

Expected:

- the shared red pattern clears or shrinks
- if failures remain, they are more clearly module-specific

## Task 3: Close The Remaining Runtime-Contract Gaps

**Files:**
- Modify: `tests/integration_tests/test_btserver.py`
- Modify: `tests/integration_tests/test_valheim.py`
- Modify: `tests/smoke_tests/run_btserver.sh`
- Modify: `tests/smoke_tests/run_valheim.sh`
- Modify: `tests/unit_tests/test_runtime_contract_static.py`
- Create: `tests/unit_tests/test_integration_runtime_policy.py`
- Modify: `docs/improvement-roadmap.md`
- Modify: `docs/servers/valheim.md`
- Modify: `docs/servers/btserver.md`
- Modify: `changelog.txt`

- [ ] **Step 1: Audit remaining process-first Docker-capable tests**

Run:

```bash
rg -n 'require_command\\("screen"\\)|runtime_backend="process"|runtime_backend="auto"|module_name=' tests/integration_tests
rg -n "get_runtime_requirements|get_container_spec" src/gamemodules
```

Expected:

- a concrete list of test files that still behave process-first while their modules declare Docker-capable runtime metadata

- [ ] **Step 2: Add static/unit coverage for any shared runtime-lane policy extracted from that audit**

Create `tests/unit_tests/test_integration_runtime_policy.py` with tests shaped like:

```python
from tests.integration_tests import conftest as integration_conftest


def test_known_docker_capable_modules_default_to_explicit_ci_runtime():
    assert integration_conftest.ci_runtime_backend_for("btserver") == "docker"
    assert integration_conftest.ci_runtime_backend_for("valheim") == "docker"


def test_local_runtime_backend_remains_non_integration_default():
    assert integration_conftest.local_runtime_backend_for("btserver") == "process"
```

- [ ] **Step 3: Resolve the `btserver` / `valheim` A2S question explicitly**

Make one of these outcomes true in code and docs:

```python
def test_btserver_prefers_a2s_when_docker_query_surface_is_proven():
    assert runtime_contract_for("btserver").query_mode == "a2s"


def test_valheim_honestly_downgrades_to_generic_query_when_a2s_is_not_proven():
    assert runtime_contract_for("valheim").query_mode in {"a2s", "udp", "tcp"}
```

The important constraint is not the exact final mode; it is that the unit/static contract and the smoke/integration/docs story all agree.

- [ ] **Step 4: Verify locally with unit/static tests only**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/cosmosquark/.pyenv/versions/alphagsm/bin/python -m pytest -q tests/unit_tests/test_runtime_contract_static.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/cosmosquark/.pyenv/versions/alphagsm/bin/python -m pytest -q tests/unit_tests/test_integration_runtime_policy.py
```

Expected:

- runtime-lane and contract tests pass locally without launching full integration flows

- [ ] **Step 5: Push and confirm the CI-only integration verdict**

```bash
git add tests/integration_tests/test_btserver.py tests/integration_tests/test_valheim.py tests/smoke_tests/run_btserver.sh tests/smoke_tests/run_valheim.sh tests/unit_tests/test_runtime_contract_static.py tests/unit_tests/test_integration_runtime_policy.py docs/servers/valheim.md docs/servers/btserver.md docs/improvement-roadmap.md changelog.txt
git commit -m "runtime: close remaining docker contract gaps"
git push -u origin release_v1
gh pr checks 36 --watch --interval 10
```

Expected:

- CI proves whether the Docker-lane contract now holds
- no local integration run is used as the source of truth

## Task 4: Build The Support-State Backlog Queue And Execute It In Gated Microcycles

**Files:**
- Modify: `docs/TEST_STATUS.md`
- Modify: `enabled_byo_servers.conf`
- Modify: `disabled_servers.conf`
- Modify: `docs/improvement-roadmap.md`
- Modify: `changelog.txt`
- Modify: `docs/servers/abfserver.md`
- Modify: `docs/servers/bobserver.md`
- Modify: `docs/servers/counterstrikeglobaloffensive.md`
- Modify: `tests/unit_tests/gamemodules/helpers.py`

- [ ] **Step 1: Freeze support-state work until Tasks 2 and 3 stop hiding unrelated red gates**

Run:

```bash
gh pr checks 36
```

Expected:

- either the CI picture is stable enough to identify module-specific support-state work
- or the answer is “not yet”, in which case do not start backlog promotions

- [ ] **Step 2: Prepare a candidate queue from the existing source-of-truth files**

Run:

```bash
sed -n '1,220p' enabled_byo_servers.conf
sed -n '1,220p' disabled_servers.conf
sed -n '1,260p' docs/TEST_STATUS.md
```

Expected:

- a short candidate set for `ENABLED (BYO)` promotions where authoritative downloads seem plausible
- a short re-verification list for `abfserver`, `bobserver`, and legacy `counterstrikeglobaloffensive`

- [ ] **Step 3: Execute support-state work one module at a time with subagents**

For each chosen module, the subagent brief must require:

```text
1. inspect the module install path and upstream source
2. add or extend unit tests before changing module logic when a unit seam exists
3. do not run integration locally
4. update docs/TEST_STATUS.md, the matching server guide, and changelog.txt in the same change
5. report whether the module should become PASSED, stay ENABLED (BYO), move to ENABLED (AUTH), or remain DISABLED
```

For the three currently known disabled modules, the exact guide paths are:

```text
docs/servers/abfserver.md
docs/servers/bobserver.md
docs/servers/counterstrikeglobaloffensive.md
```

For any BYO promotion beyond those three, the controller must record the exact
guide path in the subagent brief before code changes begin.

- [ ] **Step 4: Apply opportunistic unit-test-helper cleanup only in touched suites**

When a touched module coverage file still duplicates local dummy helpers, normalize it toward:

```python
from tests.unit_tests.gamemodules.helpers import DummyData, DummyServer
```

Do not make `tests/unit_tests/gamemodules/helpers.py` a stand-alone refactor target.

- [ ] **Step 5: Commit each support-state microcycle independently**

Use commit messages shaped like:

```bash
git commit -m "support: promote cod2server from enabled-byo"
git commit -m "support: reverify disabled bobserver"
```

Only include one module or one tiny related batch per commit.

## Task 5: Close The Program Cleanly

**Files:**
- Modify: `docs/improvement-roadmap.md`
- Modify: `changelog.txt`

- [ ] **Step 1: Mark each non-future roadmap item as done or evidence-backed open**

Use wording shaped like:

```markdown
- **Done:** broad CI batch failures were classified and the remaining red lanes
  are now tracked as module-specific follow-ups.
- **Done:** remaining process-first Docker-capable lanes were audited.
- **Open with evidence:** `bobserver` remains disabled because its latest
  blocker is now described explicitly in the roadmap note instead of being left
  as an ambiguous disabled row.
```

- [ ] **Step 2: Run the final local non-integration verification slice**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/cosmosquark/.pyenv/versions/alphagsm/bin/python -m pytest -q tests/unit_tests/test_ci_game_test_routing.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/cosmosquark/.pyenv/versions/alphagsm/bin/python -m pytest -q tests/unit_tests/test_integration_conftest_helpers.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/cosmosquark/.pyenv/versions/alphagsm/bin/python -m pytest -q tests/unit_tests/test_runtime_contract_static.py
```

Expected:

- final local safety checks are green

- [ ] **Step 3: Confirm the final integration state only through GitHub CI**

Run:

```bash
gh pr checks 36
gh run list --workflow "AlphaGSM PR" --limit 3 --json databaseId,status,conclusion,headSha,createdAt,updatedAt,displayTitle
```

Expected:

- CI is the final source of truth for integration/smoke outcomes

- [ ] **Step 4: Commit the final backlog state sync**

```bash
git add docs/improvement-roadmap.md changelog.txt
git commit -m "docs: close backlog execution loop"
```
