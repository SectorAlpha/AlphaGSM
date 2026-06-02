#!/usr/bin/env bash
# DISABLED: Current Zombie Panic! Dedicated Server smoke runner.
# SteamCMD app 4523420 stages the new GoldSrc dedicated payload, but Docker
# hlds_run still crashes at "SteamAPI_Init() failed; create pipe failed" after
# loading /root/.steam/sdk32/steamclient.so, before A2S readiness.
echo "Smoke test for zpsserver is disabled - see docs/TEST_STATUS.md for the current Steam bootstrap blocker"
exit 0
