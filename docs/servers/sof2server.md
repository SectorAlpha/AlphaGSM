# Soldier of Fortune 2: Double Helix Gold

This guide covers the `sof2server` module in AlphaGSM.

## Requirements

- `screen`
- user-provided Soldier of Fortune 2 dedicated-server files
- 32-bit runtime compatibility for the original server binary

## Quick Start

```bash
alphagsm mysof2 create sof2server
alphagsm mysof2 setup
alphagsm mysof2 start
alphagsm mysof2 status
alphagsm mysof2 stop
```

## Notes

- Module name: `sof2server`
- Install mode: bring-your-own server files
- Default port: `20100`
- Query/info protocol: `quake` on the game port
- Executable: `./sof2ded`

## Developer Notes

- AlphaGSM follows LinuxGSM's launch defaults for `sof2ded`, including `sv_punkbuster 0`, `dedicated 2`, `net_ip`, `net_port`, `+exec base/<server-name>.cfg`, and the default map `mp_shop`.
- LinuxGSM marks SOF2 as an idTech3-family server with `protocol-quake3`, so AlphaGSM uses the existing Quake UDP query/info path.
- Automated install is not provided because no authoritative LinuxGSM-backed download path was identified for this legacy server.