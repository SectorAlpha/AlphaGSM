#!/usr/bin/env bash
# ENABLED (AUTH): Zombie Panic! Dedicated Server app 4523420 installs
# anonymously, but the validated Linux launch still expects a real Steam
# client session. Even with the SteamDB-advertised -steam -secure flags, HLDS
# reports SteamAPI_IsSteamRunning() missing under the anonymous Docker lane.
echo "Smoke test for zpsserver is ENABLED (AUTH) - run an authenticated Steam client session alongside app 4523420 before start; see docs/servers/zpsserver.md"
exit 77
