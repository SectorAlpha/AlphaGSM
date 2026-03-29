# Smoke-Driven Docs

| Field | Value |
| --- | --- |
| Purpose | Keep user-facing docs aligned with the real working command flow. |
| Use when | Updating `README.md`, `docs/`, or server guides. |
| Main source | `tests/smoke_tests/` first, then integration tests and module code. |

| Field | Value |
| --- | --- |
| Inputs | Smoke runners, integration tests, current docs, and lifecycle command order. |
| Outputs | Simpler user docs with exact working commands and realistic examples. |
| Related files | `README.md`, `docs/README.md`, `docs/servers/*.md`, `tests/smoke_tests/*.sh`, `tests/integration_tests/*`. |

Use this skill when updating user-facing documentation in AlphaGSM.

## Goal

Write docs that match the real working server lifecycle in this repository.

## Best Sources

Read these first:

1. `tests/smoke_tests/run_minecraft_vanilla.sh`
2. `tests/smoke_tests/run_tf2.sh`
3. matching `tests/integration_tests/` files
4. matching game module implementation

## Rules

- Prefer exact commands over abstract descriptions.
- Keep `README.md` easy for a non-technical user to follow.
- Treat smoke-test command order as the canonical user flow.
- If the smoke test uses an important `set` step, include it.
- If the smoke test shows a full working lifecycle, summarize that lifecycle in the docs.

## Running Smoke Tests

Run all smoke tests:

```bash
make smoke-test
```

Run a single smoke test:

```bash
make smoke-test SMOKE_TEST=run_minecraft_vanilla.sh
```

Or run the script directly:

```bash
bash tests/smoke_tests/run_minecraft_vanilla.sh
```

## Main Targets

- `README.md`
- `docs/README.md`
- `docs/servers/*.md`
