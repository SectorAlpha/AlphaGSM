---
name: alphagsm-provider-requirements
description: "Use when implementing provider credentials, tokens, licenses, provisioning or an AUTH/BYO override path."
---

# Model provider prerequisites

Read [shared game helpers](../../src/utils/gamemodules/common.py), module/guide and [provider contract](../../AGENTS.md). Establish whether the upstream requirement is provider-managed auth/token/license/provisioning or operator-supplied owned assets/exports/archive URL/local service. Research upstream docs when classification is unclear.

Declare `get_provider_requirements(server)` for provider-backed paths and validate with `validate_provider_requirements(...)` at the correct lifecycle phase. Use existing categories: provider-auth, provider-token, provider-license, provider-provisioning. Missing requirements should fail with an actionable description while secret values remain private.

If a staged override is supported, keep the shared provider metadata for the auth path and a minimal explicit branch validating the actual override. Do not abandon the shared API or treat a supplied string as proof of accessible owned assets. Keep credential storage separate from ordinary datastore/evidence.

Example: a Steam-auth-gated download with an owned-files override has an AUTH default path and a validated BYO override. Tests cover missing auth, valid override, invalid override and secret-free errors. Use the shared session-only `alphagsm steam-auth login PROFILE USERNAME` flow for authenticated file acquisition. [Auth profiles](../../docs/steamcmd-auth.md) keep cached sessions private; never put passwords in module recipes or server datastore settings. Local profile presence does not prove Valve authentication or entitlement.

Align enabled_auth_servers.conf, enabled_byo_servers.conf, TEST_STATUS and guide wording with the real prerequisite. Integration validation supplies legitimate fixtures or records a concrete missing external requirement; it cannot fabricate provider credentials. Use [server-enablement](../alphagsm-server-enablement/SKILL.md) for tracker closure and [server-settings](../alphagsm-server-settings/SKILL.md) for operational secret handling.
