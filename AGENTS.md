# AlphaGSM Agent Guide

This file is for coding agents and automation working inside this repository.

## Main Rule

Use the smoke tests as the most reliable example of how a server is supposed to be:

- created
- set up
- started
- checked
- stopped

Current smoke runners:

- `smoke_tests/run_minecraft_vanilla.sh`
- `smoke_tests/run_tf2.sh`

If code comments and docs disagree, check the smoke runners first.

## Documentation Split

Keep documentation split by audience:

- `README.md`
  simple, non-technical, copy-paste friendly
- `docs/`
  user-facing server guides
- `DEVELOPERS.md`
  technical, detailed, implementation-focused

## When Behaviour Changes

Update these in order when relevant:

1. the smoke test
2. the matching server guide
3. `README.md`
4. `DEVELOPERS.md`

## Quality Gates

- lint with `bash ./lint.sh`
- keep the lint score at `10.00/10`
- keep unit tests in `tests/` green
- keep integration tests in `integration_tests/` green
- keep smoke tests in `smoke_tests/` accurate

## Known Exception

`downloadermodules/steamcmd.py` is legacy parser-broken code and is intentionally outside the active lint/docstring verification surface.

## Repo Skills

See:

- `SKILLS.md`
- `skills/smoke-driven-docs/SKILL.md`
- `skills/server-lifecycle/SKILL.md`
- `skills/install-layout/SKILL.md`
- `skills/wiki-publishing/SKILL.md`
- `skills/system-install-validation/SKILL.md`
