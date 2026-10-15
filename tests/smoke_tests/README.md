# Smoke Tests

This directory contains direct runner-style checks intended for CI and manual
verification.

Unlike the pytest-based integration tests, these scripts stream command output
directly to the terminal or CI log as they run.

Current smoke tests:

- `run_sector_alpha_agent.sh`
  Exercises the single `gameserver-api.sector-alpha.net` agent origin, trusted
  local upgrades from the old official website origin, preserved custom providers,
  independent opt-ins, private credential storage, strict contracts,
  local revocation, no-replay journaling, bounded lifecycle helper timeout and
  hostile public protocol parsing. Guided single/bulk binding uses isolated local
  inventories and mocked registration/address discovery; no public destination is contacted.
  Hostname publication checks cover complete DNS/machine-IP matching, withdrawal,
  repair, bounded DNS lifetimes and explicit pinned endpoint diagnostics.
  Individual and wildcard binding cover distinct Minecraft/TF2 subdomains on one
  public IP, per-game ports, preserved repeat runs and independent endpoint edits.
  Player connection ports are approved separately from query ports, with NAT
  overrides, legacy report compatibility and no new metadata before rebinding.
  The Minecraft integration test also proves inferred binding, agent restart and duplicate delivery
  against the selected process/Docker runtime.

- `run_minecraft_vanilla.sh`
  Creates a temporary AlphaGSM config, downloads a vanilla Minecraft server,
  starts it, checks status, sends a message, stops it, and verifies shutdown.
- `run_tf2.sh`
  Creates a temporary AlphaGSM config, downloads a TF2 dedicated server via
  SteamCMD, starts it, checks Source query status, stops it, and verifies
  shutdown.
