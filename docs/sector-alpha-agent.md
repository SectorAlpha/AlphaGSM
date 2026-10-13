# Optional Sector Alpha connection

AlphaGSM works locally without this connection. The optional agent initiates
outbound HTTPS; it does not open a management listener. Reporting and remote
management are independent opt-ins, and publication is chosen for each server.
The initial service supports Minecraft Java vanilla/Paper and Team Fortress 2.

On a compatible Sector Alpha website, sign into the verified operator account
with MFA, choose capabilities and create a ten-minute enrollment code. Locally:

```sh
alphagsm agent enroll
alphagsm agent status
```

Enter the fixed HTTPS origin and code at the prompts. The code/credentials must
not be placed in shell arguments or history. Enrollment leaves both capabilities
disabled. Create one server binding in the owner's website workspace, then bind
that opaque ID to exactly one existing local tag (replace the example values):

```sh
alphagsm agent bind BINDING_ID my-minecraft --epoch 1 \
  --game minecraft.vanilla --host game.example.net --port 25565 \
  --name 'Our Minecraft world' --capacity 20 --publish \
  --actions status start stop restart
alphagsm agent enable-reporting
alphagsm agent report-once
alphagsm agent enable-management
alphagsm agent run
```

Use only the actions you want to grant; an empty action list grants no management
operations. `--publish` is optional and independent of actions. A private server
can be managed without a directory listing. Run remains an explicit foreground
service; install it under a user service manager if continuous operation is wanted.
No background service is installed automatically. Reporting reconciles approved
local name/capacity after successful local changes and every roughly 60 seconds.
Advertised host/port remain an explicit local choice. The compatible service
requires a separate public-name challenge before granting endpoint verification.

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
