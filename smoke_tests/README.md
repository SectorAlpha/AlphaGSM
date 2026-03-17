# Smoke Tests

This directory contains direct runner-style checks intended for CI and manual
verification.

Unlike the pytest-based integration tests, these scripts stream command output
directly to the terminal or CI log as they run.

Current smoke test:

- `run_minecraft_vanilla.sh`
  Creates a temporary AlphaGSM config, downloads a vanilla Minecraft server,
  starts it, checks status, sends a message, stops it, and verifies shutdown.
- `run_tf2.sh`
  Creates a temporary AlphaGSM config, downloads a TF2 dedicated server via
  SteamCMD, starts it, checks Source query status, stops it, and verifies
  shutdown.
