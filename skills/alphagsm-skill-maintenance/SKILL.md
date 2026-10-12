---
name: alphagsm-skill-maintenance
description: "Use when authoring or validating AlphaGSM skills, discovery links, routing and behavioral evaluations."
---

# Maintain the skill library

Read [catalogue](../../SKILLS.md), [packaging conventions](../README.md) and [AGENTS.md](../../AGENTS.md). A skill captures task-specific decisions the agent would otherwise miss; avoid generic advice, duplicated module manuals and catch-all triggers. Preserve stable skill paths/names unless a migration is deliberate.

Create `skills/<name>/SKILL.md` with YAML name/description and a focused workflow. Use references only for substantial shared/conditional detail, with Markdown links from the entry point. Include inputs, actual command/source surfaces, bounded failure handling, observable completion and one realistic example. Keep skill instructions within the user's scope and execution permissions.

Add `.agents/skills/<name>` as a relative directory symlink to `../../skills/<name>` and a catalogue row. Do not maintain a second copied instruction set. If Git materializes links as text stubs, explicit loading from SKILLS.md remains available; do not claim native discovery works in that checkout.

```bash
make skills-check
PYTHONPATH=.:src python3 -m pytest tests/unit_tests/test_agent_skills_validation.py
```

Structural validation checks YAML/names/catalogue/inline local references/discovery targets without network or server mutation. It cannot prove the agent makes sound operational decisions. Use [evaluation scenarios](references/evaluation-scenarios.md) with neutral task inputs, minimal raw artifacts, and isolated scratch execution. Record baseline gaps before adding instructions, then compare actual outcomes; evaluate each new skill's task, not just its headings.

Example: a restore skill must distinguish list from restore, preserve the chosen archive and prove recovered service. Test that behavior with a disposable target. Reject duplicate names/broken references before CI. Update catalogue, discovery, relevant docs and changelog; retain precise evaluation limitations and avoid claiming unevaluated capabilities.
