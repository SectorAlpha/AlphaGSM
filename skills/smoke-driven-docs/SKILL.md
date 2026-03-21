# Smoke-Driven Docs

Use this skill when updating user-facing documentation in AlphaGSM.

## Goal

Write docs that match the real working server lifecycle in this repository.

## Best Sources

Read these first:

1. `smoke_tests/run_minecraft_vanilla.sh`
2. `smoke_tests/run_tf2.sh`
3. matching `integration_tests/` files
4. matching game module implementation

## Rules

- Prefer exact commands over abstract descriptions.
- Keep `README.md` easy for a non-technical user to follow.
- Treat smoke-test command order as the canonical user flow.
- If the smoke test uses an important `set` step, include it.
- If the smoke test shows a full working lifecycle, summarize that lifecycle in the docs.

## Main Targets

- `README.md`
- `docs/README.md`
- `docs/servers/*.md`
