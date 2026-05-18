# Medal of Honor: Allied Assault

This guide covers the `mohaaserver` module in AlphaGSM.

## Requirements

- `screen`
- user-provided Medal of Honor: Allied Assault dedicated-server files
- 32-bit runtime compatibility for the original server binary

## Quick Start

```bash
alphagsm mymohaa create mohaaserver
alphagsm mymohaa setup
alphagsm mymohaa start
alphagsm mymohaa status
alphagsm mymohaa stop
```

## Notes

- Module name: `mohaaserver`
- Install mode: bring-your-own server files
- Default port: `12203`
- Query/info protocol: `udp` reachability on the game port
- Executable: `./mohaa_lnxded`

## Developer Notes

- AlphaGSM follows LinuxGSM's launch defaults for `mohaa_lnxded`, including `fs_basepath`, `fs_outputpath`, `dedicated 2`, `net_ip`, `net_port`, the default map `dm/mohdm1`, and `+exec main/<server-name>.cfg`.
- LinuxGSM does not advertise an external query protocol for MOHAA, so AlphaGSM intentionally exposes only a conservative UDP reachability probe for `query` and `info`.
- Automated install is not provided because no authoritative LinuxGSM-backed download path was identified for this legacy server.