"""Bounded remote-CI observations; these never replace AlphaGSM readiness checks."""

import argparse
import json
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess

INFO_REQUEST = b"\xff\xff\xff\xffTSource Engine Query\0"


def probe_a2s(family, address, port, timeout=2):
    """Record one real INFO exchange, including the optional server challenge."""
    result = {"family": "ipv6" if family == socket.AF_INET6 else "ipv4", "address": address, "port": port}
    try:
        with socket.socket(family, socket.SOCK_DGRAM) as transport:
            transport.settimeout(timeout)
            transport.connect((address, port))
            transport.send(INFO_REQUEST)
            packet = transport.recv(4096)
            if packet[:5] == b"\xff\xff\xff\xffA" and len(packet) >= 9:
                result["challenge"] = packet[5:9].hex()
                transport.send(INFO_REQUEST + packet[5:9])
                packet = transport.recv(4096)
        result["packet_prefix"] = packet[:40].hex()
        result["packet_bytes"] = len(packet)
        if packet[:5] == b"\xff\xff\xff\xffI":
            fields = packet[6:].split(b"\0", 4)
            if len(fields) != 5 or len(fields[4]) < 5:
                result["error"] = "Malformed A2S_INFO response"
            else:
                result.update(protocol="a2s", name=fields[0].decode("utf-8", "replace"),
                              map=fields[1].decode("utf-8", "replace"),
                              players=fields[4][2], max_players=fields[4][3])
    except OSError as error:
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def _bounded_text(path, limit=2500, tail=True):
    try:
        with path.open("rb") as stream:
            if tail:
                stream.seek(0, 2)
                stream.seek(max(0, stream.tell() - limit))
            return stream.read(limit).decode("utf-8", "replace")
    except OSError as error:
        return f"{type(error).__name__}: {error}"


def _native_details(install):
    """Inspect only this disposable install and its native game processes."""
    install = Path(install).resolve()
    details = {"steam_libraries": [], "native_logs": []}
    for process in list(Path("/proc").glob("[0-9]*"))[:512]:
        try:
            if not (process / "comm").read_text().lower().startswith("wreckfest"):
                continue
            if not (process / "cwd").resolve().is_relative_to(install):
                continue
            maps = _bounded_text(process / "maps", 512000, tail=False).splitlines()
            libraries = sorted({line.split(None, 5)[-1] for line in maps
                                if "steam" in line.lower() and ".dll" in line.lower()})[:20]
            details["steam_libraries"].append({"pid": int(process.name), "paths": libraries})
        except OSError:
            continue
    candidates = [install / "log.txt", install / "logs/connection_log.txt", install / "logs/console_log.txt"]
    prefix = install / ".alphagsm-wineprefix/drive_c"
    for steam_root in (prefix / "Program Files (x86)/Steam", prefix / "Program Files/Steam"):
        candidates.extend(steam_root / "logs" / name for name in ("connection_log.txt", "console_log.txt"))
    for candidate in candidates:
        if candidate.is_file() and candidate.resolve().is_relative_to(install):
            details["native_logs"].append({"path": str(candidate.relative_to(install)),
                                           "network_tail": safe_network_tail(_bounded_text(candidate))})
    return details


def safe_network_tail(text):
    """Keep only network/init lines and discard whole credential-bearing lines."""
    allowed = re.compile(r"socket|bind|ipv[46]|port|server connected|server init|failed to init", re.I)
    sensitive = re.compile(r"passw|token|ticket|secret|auth|credential|cookie|key|login|://", re.I)
    return "\n".join(line for line in text.splitlines() if allowed.search(line) and not sensitive.search(line))


def decode_inet_diag(message, port):
    """Read Linux inet_diag_msg plus its INET_DIAG_SKV6ONLY attribute."""
    if len(message) < 72 or message[0] != socket.AF_INET6:
        return None
    local_port = struct.unpack_from("!H", message, 4)[0]
    if local_port != port:
        return None
    result = {"address": socket.inet_ntop(socket.AF_INET6, message[8:24]), "port": local_port,
              "inode": struct.unpack_from("=I", message, 68)[0], "v6only": None}
    offset = 72
    while offset + 4 <= len(message):
        length, kind = struct.unpack_from("=HH", message, offset)
        if length < 4 or offset + length > len(message):
            break
        if kind == 11 and length >= 5:  # INET_DIAG_SKV6ONLY, a response-only u8.
            result["v6only"] = bool(message[offset + 4])
        offset += (length + 3) & ~3
    return result


def _socket_v6only(port):
    """Use read-only NETLINK_SOCK_DIAG where minimal images have no ss binary."""
    # Linux include/uapi/linux/{inet_diag,sock_diag}.h; no socket is modified.
    request = struct.pack("=BBBBI", socket.AF_INET6, socket.IPPROTO_UDP, 0, 0, 0xffffffff)
    request += bytes(40) + b"\xff" * 8
    header = struct.pack("=IHHII", 16 + len(request), 20, 0x301, 1, 0)
    records = []
    try:
        with socket.socket(socket.AF_NETLINK, socket.SOCK_DGRAM, 4) as transport:
            transport.settimeout(2)
            transport.sendto(header + request, (0, 0))
            for _ in range(8):
                packet = transport.recv(65535)
                offset = 0
                while offset + 16 <= len(packet):
                    length, kind = struct.unpack_from("=IH", packet, offset)
                    if length < 16 or offset + length > len(packet):
                        return {"records": records, "error": "Malformed netlink message"}
                    if kind == 3:  # NLMSG_DONE
                        return {"records": records}
                    if kind == 2:  # NLMSG_ERROR
                        return {"records": records, "error": "Kernel rejected socket diagnostic request"}
                    record = decode_inet_diag(packet[offset + 16:offset + length], port)
                    if record:
                        records.append(record)
                    offset += (length + 3) & ~3
            return {"records": records, "error": "Socket diagnostic dump exceeded bounded reads"}
    except (OSError, AttributeError) as error:
        return {"records": records, "error": f"{type(error).__name__}: {error}"}


def snapshot(port, install, quick=False):
    """Compare IPv4, IPv6 and mapped IPv4 from the current network namespace."""
    result = {"phase": "post_start" if quick else "failure", "a2s": [
        probe_a2s(family, address, port, timeout=0.25 if quick else 2) for family, address in (
        (socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1"),
        (socket.AF_INET6, "::ffff:127.0.0.1"))], **_native_details(install)}
    # This is only the namespace default; applications may override it per socket.
    result["bindv6only_default"] = _bounded_text(Path("/proc/sys/net/ipv6/bindv6only"), 40, tail=False).strip()
    result["query_socket_v6only"] = _socket_v6only(port)
    if shutil.which("ss"):
        command = ["ss", "-uanep", "--inet-sockopt", "sport", "=", f":{port}"]
        try:
            observed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=5)
            result["socket_options"] = {"returncode": observed.returncode,
                                         "stdout": observed.stdout[:6000], "stderr": observed.stderr[:1000]}
        except (OSError, subprocess.TimeoutExpired) as error:
            result["socket_options"] = {"error": f"{type(error).__name__}: {error}"}
    else:
        result["socket_options"] = {"unavailable": "ss is not installed"}
    return result


def collect_remote_diagnostics(port, install, container=None, quick=False):
    """Print observations without promoting a diagnostic response into readiness."""
    print("[diagnostic] Wreckfest host address-family snapshot: " + json.dumps(snapshot(port, install, quick)), flush=True)
    if container:
        source = Path(__file__).read_text(encoding="utf-8")
        command = ["docker", "exec", "-i", container, "python3", "-", "--inside", str(port), "/srv/server"]
        if quick:
            command.append("--quick")
        try:
            result = subprocess.run(command, input=source, capture_output=True, text=True, check=False, timeout=30)
            print("[diagnostic] Wreckfest container address-family snapshot: " + json.dumps({
                "returncode": result.returncode, "stdout": result.stdout[:18000], "stderr": result.stderr[:1000]}), flush=True)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f"[diagnostic] Wreckfest container observation failed: {type(error).__name__}: {error}", flush=True)


def main():
    """Support the smoke runner and stdin-fed container observer."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inside", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("port", type=int)
    parser.add_argument("install")
    parser.add_argument("--container")
    arguments = parser.parse_args()
    if not 1 <= arguments.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if arguments.inside:
        print(json.dumps(snapshot(arguments.port, arguments.install, arguments.quick)), flush=True)
    else:
        collect_remote_diagnostics(arguments.port, arguments.install, arguments.container, arguments.quick)


if __name__ == "__main__":
    main()
