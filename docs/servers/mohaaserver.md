# Medal of Honor: Allied Assault

This guide covers the `mohaaserver` module in AlphaGSM.

`mohaaserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that owned-dedicated-tree
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- an owned Medal of Honor: Allied Assault dedicated-server tree
- 32-bit runtime compatibility for the original server binary

## Quick Start

```bash
alphagsm mymohaa create mohaaserver
alphagsm mymohaa setup
alphagsm mymohaa start
alphagsm mymohaa status
alphagsm mymohaa stop
```

`mohaaserver` is supported in `ENABLED (BYO)` mode. Before `setup` or `start`,
copy an owned MOHAA dedicated server tree into your chosen `<install_dir>/` so
`<install_dir>/mohaa_lnxded` exists.

Suggested flow:

```bash
alphagsm mymohaa create mohaaserver
alphagsm mymohaa setup -n 12203 /path/to/mohaaserver
# copy the owned MOHAA dedicated server files into /path/to/mohaaserver/
alphagsm mymohaa start
```

## Notes

- Module name: `mohaaserver`
- Install mode: ENABLED (BYO) server files
- Default port: `12203`
- Query/info protocol: `udp` reachability on the game port
- Executable: `./mohaa_lnxded`

## Developer Notes

- AlphaGSM follows LinuxGSM's launch defaults for `mohaa_lnxded`, including `fs_basepath`, `fs_outputpath`, `dedicated 2`, `net_ip`, `net_port`, the default map `dm/mohdm1`, and `+exec main/<server-name>.cfg`.
- LinuxGSM does not advertise an external query protocol for MOHAA, so AlphaGSM intentionally exposes only a conservative UDP reachability probe for `query` and `info`.
- Automated install is not provided because no authoritative LinuxGSM-backed download path was identified for this legacy server.
