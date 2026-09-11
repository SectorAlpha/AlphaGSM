# Soldier of Fortune 2: Double Helix Gold

This guide covers the `sof2server` module in AlphaGSM.

`sof2server` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that owned-dedicated-tree
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- an owned Soldier of Fortune 2 dedicated-server tree
- 32-bit runtime compatibility for the original server binary

## Quick Start

```bash
alphagsm mysof2 create sof2server
alphagsm mysof2 setup
alphagsm mysof2 start
alphagsm mysof2 status
alphagsm mysof2 stop
```

`sof2server` is supported in `ENABLED (BYO)` mode. Before `setup` or `start`,
copy an owned SOF2 dedicated server tree into your chosen `<install_dir>/` so
`<install_dir>/sof2ded` exists.

Suggested flow:

```bash
alphagsm mysof2 create sof2server
alphagsm mysof2 setup -n 20100 /path/to/sof2server
# copy the owned SOF2 dedicated server files into /path/to/sof2server/
alphagsm mysof2 start
```

## Notes

- Module name: `sof2server`
- Install mode: ENABLED (BYO) server files
- Default port: `20100`
- Query/info protocol: `quake` on the game port
- Executable: `./sof2ded`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create sof2server`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

## Developer Notes

- AlphaGSM follows LinuxGSM's launch defaults for `sof2ded`, including `sv_punkbuster 0`, `dedicated 2`, `net_ip`, `net_port`, `+exec base/<server-name>.cfg`, and the default map `mp_shop`.
- LinuxGSM marks SOF2 as an idTech3-family server with `protocol-quake3`, so AlphaGSM uses the existing Quake UDP query/info path.
- Automated install is not provided because no authoritative LinuxGSM-backed download path was identified for this legacy server.
