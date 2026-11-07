---
name: alphagsm-port-claims
description: "Use when implementing or debugging AlphaGSM port ownership, collision checks and claim-bearing edits."
---

# Preserve port ownership

Read [port manager](../../src/server/port_manager.py), [server lifecycle](../../src/server/server.py), runtime builders and [claim tests](../../tests/unit_tests/server/test_port_manager.py). Reproduce with two explicit tags or a real local listener in an isolated config.

Model the whole claimed set: primary game port, optional `*port` values, hosted IP fields (including wildcard overlap), and runtime-published ports. Collision checks ignore protocol, so UDP and TCP declarations do not let two servers claim the same hosted IP/port. Test optional ports and custom published mappings, not just main game ports.

Required behavior:

- `set` rejects conflicting claim changes before persistence, including IP/runtime ports edits.
- `setup` may shift the entire claimed set together only for default-owned claims. Explicit claim ownership remains sticky across later setup until the user changes it.
- `start` fails before `prestart` when another AlphaGSM owner or live listener conflicts on the same hosted IP.

Example: a runtime TCP publication overlaps another server's UDP query port. Reject the edit immediately; no prestart/install side effects or hidden protocol exemption is allowed.

Add behavior tests for the reproduced collision, preserved datastore/claim state, default-set shift and explicit reuse. Include hook-order coverage for start rejection. Avoid bypassing the manager by editing persisted claims manually, freeing an unrelated owner's listener, or silently moving an explicit port. Verify both process and Docker-derived claims when changing shared builders; update docs/changelog for operator-visible behavior.
