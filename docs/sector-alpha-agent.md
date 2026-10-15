# Optional Sector Alpha connection

AlphaGSM works locally without this connection. The optional agent initiates
outbound HTTPS; it does not open a management listener. Reporting and remote
management are independent opt-ins, and publication is chosen for each server.
Public player-stat queries support Minecraft Java vanilla/Paper and Team Fortress 2.
Other managed games can use private reporting and permitted remote actions.

On a compatible Sector Alpha website, sign into the verified operator account
with MFA, choose capabilities and create a ten-minute enrollment code. Locally:

```sh
alphagsm agent enroll
alphagsm agent bind '*'
```

Enter the enrollment code at its hidden prompt. The default website is
`https://sector-alpha.net`; use `agent enroll --origin https://your-site.example`
for another compatible service. Never put codes or credentials in shell arguments.

`agent bind '*'` discovers all eligible servers owned by your local AlphaGSM user,
registers their website bindings, and saves the returned IDs automatically. Quote
`'*'` so your shell passes it literally instead of expanding local filenames.
For one server use `alphagsm agent bind my-minecraft`. `alphagsm agent setup`
combines bulk binding with enrollment if needed. Existing bindings are reused.

The guided preview reads each server's configured game, query/game port, name and
capacity. It suggests a public numerical IP from configured networking details,
the outbound interface, or a bounded HTTPS address lookup. Confirm the advertised
host and port: NAT, VPNs and port forwarding can make the suggested endpoint wrong.
Use `--host game.example.net` to override the host and avoid address discovery;
use `--port 25566` when binding one server with a different public port.
Bulk binding keeps individual server ports. Unreadable or unconfigured servers
are reported with a reason and can be retried after fixing their local settings.

New bindings default to private with no allowed remote actions. The prompts let
you choose publication and actions; repeat runs preserve your previous choices.
Enrollment and binding leave reporting and management disabled. Enable the
capabilities you want once the preview is correct:

```sh
alphagsm agent enable-reporting
alphagsm agent report-once
alphagsm agent enable-management
alphagsm agent run
```

The full explicit form remains available for an existing website binding:

```sh
alphagsm agent bind BINDING_ID my-minecraft --epoch 1 \
  --game minecraft.vanilla --host game.example.net --port 25565 \
  --name 'Our Minecraft world' --capacity 20 --publish \
  --actions status start stop restart
```

Use only the actions you want to grant; an empty action list grants no management
operations. `--publish` is optional and independent of actions. A private server
can be managed without a directory listing. Run remains an explicit foreground
service; install it under a user service manager if continuous operation is wanted.
No background service is installed automatically. Reporting reconciles approved
local name/capacity after successful local changes and every roughly 60 seconds.
Advertised host/port remain an explicit local choice. The compatible service
requires a separate public-name challenge before granting endpoint verification.
Reporting retries temporary configuration-lock timeouts during long lifecycle
operations and resumes when the lock is released; a busy lifecycle does not
permanently terminate reporting. Publication still expires if renewal is delayed
beyond the service lease.

Normal AlphaGSM stop may force termination after graceful attempts. Restart is
stop then start and requires a running server. Status reports only running,
stopped or unknown. No remote set, console, logs, files, RCON, installs, updates,
backups, deletion, runtime/module changes, selectors or arguments are accepted.
If an operation times out or execution cannot be confirmed, check the server
locally before issuing another operation; the same job is never replayed.

```sh
alphagsm agent publication BINDING_ID off
alphagsm agent disable-management
alphagsm agent disable-reporting
alphagsm agent unbind BINDING_ID
```

Disabling reporting attempts one withdrawal report. If offline, publication
expires within ten minutes of the last accepted renewal. Disabling management
rejects queued jobs locally. Revoke the installation in the owner website to
invalidate all scoped keys and queued jobs centrally. Once both capabilities
are disabled and the old installation is revoked, `alphagsm agent forget` removes
its local credentials; the durable processed-job journal remains for recovery.

Local configuration and the journal are outside game datastores, under the
operator's AlphaGSM `agent` directory, with 0700 directory and 0600 files. Never
commit them or copy them into a game directory. Only one provider relationship
is supported. Windows enrollment fails closed until user-only credential ACLs
are implemented; this does not affect ordinary local AlphaGSM commands.

Validated gates: the offline `run_sector_alpha_agent.sh` runner covers consent,
contracts, private storage, hostile parsers, crash reconciliation and duplicates.
The Minecraft integration test additionally runs the real bounded lifecycle
helper when `ALPHAGSM_VALIDATE_AGENT=1`, using its selected process/Docker runtime.
The service repository supplies the verified HTTPS and PostgreSQL boundary tests.
Production deployment still needs real TLS, secrets and the isolated query worker
firewall described by the compatible service.

Rotate one key in the website owner dashboard, then run either
`alphagsm agent replace-credential reporting` or
`alphagsm agent replace-credential management`. Enter the key ID and secret at
the interactive prompts; management also asks for the new generation shown by
the website. Reporting rotation leaves management/jobs unchanged. Management
rotation cancels pending jobs under the old generation and leaves reporting
credentials valid. Existing local opt-ins and selected server permissions stay
unchanged; replacement cannot add a capability that was not enrolled.
