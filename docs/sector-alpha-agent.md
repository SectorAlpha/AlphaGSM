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
Use `--host game.example.net` to override the host and avoid address discovery during binding;
use `--port 25566` when binding one server with a different public port.
Bulk binding keeps individual server ports. Unreadable or unconfigured servers
are reported with a reason and can be retried after fixing their local settings.

For an existing domain/subdomain pointing to this machine:

```sh
alphagsm agent bind my-minecraft --host game.mygameserver.com
alphagsm agent check-endpoint my-minecraft
```

Before every public report, the agent checks fresh A and AAAA records. Every
advertised address must be globally routable and match this machine's configured
or detected public IP. For NAT or multiple public addresses, supply `--public-ip
YOUR_PUBLIC_IP` when binding; repeat the option for each expected address. These
expectations stay in local configuration. DNS checks still run when `--host` is
explicit. An unavailable lookup or mismatch withholds only that server's outgoing
publication; reporting continues for other bindings. Stored consent is retained,
so a later matching DNS check can restore publication. Private bindings remain
usable while DNS is being corrected. No DNS records are created or modified.

`check-endpoint` additionally tests the advertised port through the supported
native game protocol, using only matched numerical addresses. It does not change
publication or permissions. A failure may mean a stopped game, wrong forwarded
port, firewall, or missing NAT loopback support; an external test is still needed
when the router cannot reach its own public address. The website's separate
ownership challenge and isolated query checks remain required.

## Multiple game subdomains on one machine

This example connects existing AlphaGSM servers tagged `my-minecraft` and
`my-tf2` to separate subdomains on the same public IP. Run the commands as the
AlphaGSM user who owns those servers. If this machine is not enrolled yet, follow
the enrollment instructions above and run `alphagsm agent enroll` first.

1. **Point both subdomains at the game host.** In your DNS provider, create these
   records, replacing `YOUR_PUBLIC_IPV4` with the machine's actual public IPv4:

   | Type | Name | Value |
   | --- | --- | --- |
   | A | `minecraft.mygameserver.com` | `YOUR_PUBLIC_IPV4` |
   | A | `tf2.mygameserver.com` | `YOUR_PUBLIC_IPV4` |

   Use your own domain in place of `mygameserver.com`. Add AAAA records only when
   the machine has a reachable public IPv6 address supported by that game's query
   profile. The TF2/A2S public profile currently requires IPv4-only DNS answers.
   Every A/AAAA answer must match the host's expected public addresses. Wait until
   the new records resolve correctly before checking the endpoints.

2. **Bind each local game to its subdomain.** Each command infers that server's
   configured public/query port, name and capacity. Replace the example tags with
   your existing local server tags:

   ```sh
   alphagsm agent bind my-minecraft --host minecraft.mygameserver.com --publish
   alphagsm agent bind my-tf2 --host tf2.mygameserver.com --publish
   ```

   Review the host, port, publication and allowed remote actions in each preview
   before saving. If a forwarded public port differs from the local setting, add
   `--port 25566` to that individual server's command, using its actual public port.
   For NAT or multiple public addresses, add `--public-ip YOUR_PUBLIC_IPV4` to each
   binding; repeat `--public-ip` for additional expected machine addresses.

3. **Check both advertised endpoints.** Start the games through your normal
   AlphaGSM workflow and allow/forward their configured ports through the firewall
   and router. Then run:

   ```sh
   alphagsm agent check-endpoint my-minecraft
   alphagsm agent check-endpoint my-tf2
   ```

   Correct DNS or port errors before continuing. A router without NAT loopback
   may require a separate external connectivity test. The website still requires
   its own ownership challenge and isolated query verification for each endpoint.

4. **Enable and keep reporting running.** Once the previews and checks are correct:

   ```sh
   alphagsm agent enable-reporting
   alphagsm agent report-once
   alphagsm agent run
   ```

   `run` stays in the foreground; use your user service manager for continuous
   operation. Complete each endpoint's ownership challenge in the website to
   obtain verified public statistics. Reporting does not enable remote management.

You can also configure all local games in one guided pass:

```sh
alphagsm agent bind '*'
```

Enter a different `hostname:port` at each server's endpoint prompt, such as
`minecraft.mygameserver.com:25565` and `tf2.mygameserver.com:27015`, replacing the
ports with your configured public/query ports. Choose publication and actions for
each game and review every mapping in the final preview. Repeating the command
preserves existing hostnames, ports and approvals.

Every hostname is checked against the same machine independently. A DNS mismatch,
endpoint edit or publication opt-out for one binding does not change the other
games' approvals. Complete the website's ownership challenge for each endpoint.
DNS names do not select a local process or translate ports: each game needs its
configured port reachable through the firewall/NAT. Sharing the same IP and port
requires a game-compatible proxy; configuring one is outside agent binding.

## Reporting and management permissions

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
