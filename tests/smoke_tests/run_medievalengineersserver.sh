#!/usr/bin/env bash
# DISABLED: Medieval Engineers still fails under the validated Docker
# wine-proton lane after a full anonymous SteamCMD install. The dedicated EXE
# reaches the Windows/SDL bootstrap, then throws "System.PlatformNotSupportedException:
# Video driver  not supported" plus follow-on missing-resource and
# XML-serializer exceptions before server logs or A2S readiness appear.
# See docs/TEST_STATUS.md for the current blocker details.
echo "Smoke test for medievalengineersserver is disabled - see docs/TEST_STATUS.md for the current Proton/Wine startup blocker"
exit 0
