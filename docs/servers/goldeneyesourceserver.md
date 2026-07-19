# GoldenEye: Source

This guide covers the `goldeneyesourceserver` module in AlphaGSM.

`goldeneyesourceserver` is `ENABLED (BYO)`. AlphaGSM can run a complete
operator-staged GoldenEye: Source dedicated server tree through either the
process or Docker runtime, but it does not download that tree during setup.
This status does not claim a current integration pass.

## Why Setup Is BYO

The previously automated download path is not a usable server artifact in CI:

- the official `/go/` endpoint returns a 241-byte HTML meta-refresh in both
  process and Docker CI
- the authoritative ModDB release endpoint returns Cloudflare HTTP 403
- the signed official object endpoint returns HTTP 401

AlphaGSM therefore does not substitute browser endpoints or attempt to resolve
the official redirect during setup.

## Required Tree

Stage one complete directory containing both parts of the official server
installation:

- the Source SDK Base 2007 Dedicated Server files from Steam AppID `310`
- the complete GoldenEye: Source 5.0.6 `gesource` content directory
- a top-level `steam_appid.txt` containing exactly `310` as a required operator
  marker
- an executable top-level `srcds_run` launcher

The important top-level layout is:

```text
<install_dir>/
|-- srcds_run
|-- steam_appid.txt
|-- bin/
|-- hl2/
`-- gesource/
    |-- gameinfo.txt
    `-- maps/
        `-- ge_archives.bsp
```

Do not leave the Source 2007 base or `gesource` content under an extra archive
wrapper directory. `steam_appid.txt` must contain only `310` (a trailing newline
is fine). It is an accidental AppID mismatch guard and does not authenticate
asset provenance or prove the staged base came from AppID 310. Providing the
complete AppID 310 base remains the operator's responsibility. Setup also
checks the other marker paths, executable permission, and realpath containment
under `<install_dir>`; the operator-supplied tree must still contain the rest of
the preserved server content.

Internal relative symlink chains are supported because they retain
process/Docker parity. AlphaGSM deterministically inspects every symlink in the
complete staged tree without following symlinked directories. Every link hop
must remain inside `<install_dir>`; absolute links, cycles, and relative paths
that leave the tree before re-entering it are rejected, including links outside
the required marker paths.

## Artifact Check

The known GoldenEye: Source dedicated-server artifact is version `5.0.6` with
this SHA-256 digest:

```text
79643189e9d6549e13ed9545d2277cb34bac05fff645d44d9de1f0ab030610d3
```

Manually compare the artifact digest before extracting and staging its complete
`gesource` directory. AlphaGSM does not verify the artifact or treat this hash
as proof of provenance; the digest is operator guidance.

## Quick Start

Create the AlphaGSM server entry:

```bash
alphagsm mygoldeneye create goldeneyesourceserver
```

After staging the complete tree, validate it through setup:

```bash
alphagsm mygoldeneye setup 27015 /srv/goldeneye-source
```

Start and inspect the server:

```bash
alphagsm mygoldeneye start
alphagsm mygoldeneye status
alphagsm mygoldeneye query
alphagsm mygoldeneye info
```

Stop it:

```bash
alphagsm mygoldeneye stop
```

## Runtime Notes

- Module name: `goldeneyesourceserver`
- Default port: `27015` over UDP and TCP
- Default map: `ge_archives`
- Default maximum players: `16`
- Docker family: `steamcmd-linux`
- Process and Docker use the same `srcds_run -game gesource` game command
- Generic in-game broadcast messages are not currently supported
