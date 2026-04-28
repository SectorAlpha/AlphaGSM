Unimplemented `status` / Unsupported console report

Date: 2026-04-27

Summary:
- Found many gamemodule files that call `gamemodule_common.print_unsupported_message()` or whose `status` docstring says it's not implemented.
- Found `TODO` markers in `src/gamemodules/teamfortress2.py` related to downloads and filesystem updates.

Modules with unimplemented `status` / `print_unsupported_message()` (candidate list):

- src/gamemodules/cod4server.py
- src/gamemodules/armarserver.py
- src/gamemodules/craftopiaserver.py
- src/gamemodules/necserver.py
- src/gamemodules/mordserver.py
- src/gamemodules/projectzomboid.py
- src/gamemodules/smallandserver.py
- src/gamemodules/etlegacyserver.py
- src/gamemodules/scpslserver.py
- src/gamemodules/wfserver.py
- src/gamemodules/rust.py
- src/gamemodules/reignofkingsserver.py
- src/gamemodules/returntomoriaserver.py
- src/gamemodules/noonesurvivedserver.py
- src/gamemodules/enshrouded.py
- src/gamemodules/btlserver.py
- src/gamemodules/scumserver.py
- src/gamemodules/qwserver.py
- src/gamemodules/ut99server.py
- src/gamemodules/ckserver.py
- src/gamemodules/pixarkserver.py
- src/gamemodules/saleblazersserver.py
- src/gamemodules/deadmatterserver.py
- src/gamemodules/groundbranchserver.py
- src/gamemodules/q4server.py
- src/gamemodules/medievalengineersserver.py
- src/gamemodules/inssserver.py
- src/gamemodules/motortownserver.py
- src/gamemodules/pvrserver.py
- src/gamemodules/wurmserver.py
- src/gamemodules/longvinterserver.py
- src/gamemodules/stnserver.py
- src/gamemodules/codserver.py
- src/gamemodules/cod2server.py
- src/gamemodules/codwawserver.py
- src/gamemodules/bf1942server.py
- src/gamemodules/dayzarma2epochserver.py
- src/gamemodules/astroneerserver.py
- src/gamemodules/ark.py
- src/gamemodules/ut2k4server.py
- src/gamemodules/squadserver.py
- src/gamemodules/exfilserver.py
- src/gamemodules/hogwarpserver.py
- src/gamemodules/arma3headlessserver.py
- src/gamemodules/arma3desolationreduxserver.py
- src/gamemodules/sampserver.py
- src/gamemodules/dayofdragonsserver.py
- src/gamemodules/empyrionserver.py
- src/gamemodules/darkandlightserver.py
- src/gamemodules/bannerlordserver.py
- src/gamemodules/qlserver.py
- src/gamemodules/dstserver.py

TODO locations found:
- src/gamemodules/teamfortress2.py: lines referencing Steam downloads integration and an `updatefs.update(...) #TODO` comment.

Recommended next steps:
1. Prioritize which modules need a `status()` implementation (start with high-priority servers you actively manage, e.g., `cod4server.py`).
2. Implement a shared `status` helper in `utils/gamemodules/common.py` if patterns are repeated across modules.
3. For each module, implement `status(server, verbose)` to inspect logs, query ports, or call the game query protocol as appropriate.
4. Document `status` behavior and add unit/integration tests in `tests/` per the repo's New Module Test Contract when ready to run CI.

If you'd like, I can now:
- Implement a `status()` for one selected module (no tests run locally), or
- Open a PR-style patch that adds a shared `status` helper and updates a small set of modules.

