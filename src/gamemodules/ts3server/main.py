"""TeamSpeak 3 server lifecycle helpers."""

import os
import pathlib
import re
import shutil
import subprocess
import time
import urllib.request

import downloader
import screen
import server.runtime as runtime_module
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.gamemodules import common as gamemodule_common

TEAMSPEAK_DOWNLOADS_PAGE = "https://teamspeak.com/en/downloads"
TEAMSPEAK_URL_TEMPLATE = (
    "https://files.teamspeak-services.com/releases/server/%s/"
    "teamspeak3-server_linux_amd64-%s.tar.bz2"
)
TEAMSPEAK_USER_AGENT = "AlphaGSM/1.0 (+https://github.com/SectorAlpha/AlphaGSM)"
MANAGED_DB_IMAGE = "mariadb:11.5"
MANAGED_DB_ALIAS = "database"

commands = ()
command_args = gamemodule_common.build_setup_version_url_command_args(
    "The voice port to use for the TeamSpeak 3 server",
    "The directory to install TeamSpeak 3 in",
    url_option=OptSpec(
        "u",
        ["url"],
        "Direct TeamSpeak 3 server download URL to use.",
        "url",
        "URL",
        str,
    ),
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def _read_download_page():
    """Return the TeamSpeak downloads page HTML."""

    request = urllib.request.Request(
        TEAMSPEAK_DOWNLOADS_PAGE, headers={"User-Agent": TEAMSPEAK_USER_AGENT}
    )
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8")


def resolve_teamspeak_download(version=None):
    """Resolve the TeamSpeak 3 Linux server tarball URL."""

    if version not in (None, "", "latest"):
        return version, TEAMSPEAK_URL_TEMPLATE % (version, version)
    page = _read_download_page()
    match = re.search(r"releases/server/([0-9]+(?:\.[0-9]+)+)/teamspeak3-server_linux_amd64", page)
    if match is None:
        raise ServerError("Unable to locate the latest TeamSpeak 3 server version")
    version = match.group(1)
    return version, TEAMSPEAK_URL_TEMPLATE % (version, version)


def _sync_tree(source, target):
    """Recursively copy a tree into the install directory."""

    os.makedirs(target, exist_ok=True)
    for root, dirs, files in os.walk(source):
        rel_root = os.path.relpath(root, source)
        target_root = target if rel_root == "." else os.path.join(target, rel_root)
        os.makedirs(target_root, exist_ok=True)
        for dirname in dirs:
            os.makedirs(os.path.join(target_root, dirname), exist_ok=True)
        for filename in files:
            shutil.copy2(os.path.join(root, filename), os.path.join(target_root, filename))


def _resolve_archive_root(downloadpath):
    """Return the extracted archive root directory if there is one."""

    entries = [os.path.join(downloadpath, entry) for entry in os.listdir(downloadpath)]
    directories = [entry for entry in entries if os.path.isdir(entry)]
    if len(directories) == 1:
        return directories[0]
    return downloadpath


def configure(server, ask, port=None, dir=None, *, version=None, url=None, exe_name="ts3server"):
    """Collect and store configuration values for a TeamSpeak 3 server."""

    server.data.setdefault("backupfiles", ["ts3server.sqlitedb", "files", "ts3server.ini"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["ts3server.sqlitedb", "files", "ts3server.ini"]}},
            "schedule": [("default", 0, "days")],
        }

    if url is None:
        version, url = resolve_teamspeak_download(version=version)
    server.data["version"] = version
    server.data["url"] = url
    server.data["download_name"] = "teamspeak3-server_linux_amd64-%s.tar.bz2" % (version,)
    server.data.setdefault("queryport", "10011")
    server.data.setdefault("filetransferport", "30033")
    server.data.setdefault("license_accepted", True)
    server.data.setdefault("db_mode", "sqlite")

    if port is None:
        port = server.data.get("port", 9987)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the TeamSpeak 3 server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the TeamSpeak 3 server files."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if (
        "current_url" not in server.data
        or server.data["current_url"] != server.data["url"]
        or not os.path.isfile(exe_path)
    ):
        downloadpath = downloader.getpath(
            "url", (server.data["url"], server.data["download_name"], "tar.bz2")
        )
        _sync_tree(_resolve_archive_root(downloadpath), server.data["dir"])
        server.data["current_url"] = server.data["url"]
    server.data.save()


def get_start_command(server):
    """Build the command used to launch a TeamSpeak 3 server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        "./" + server.data["exe_name"],
        "default_voice_port=%s" % (server.data["port"],),
        "query_port=%s" % (server.data["queryport"],),
        "filetransfer_port=%s" % (server.data["filetransferport"],),
        "license_accepted=%s" % (1 if server.data.get("license_accepted", True) else 0,),
    ]
    if _uses_mariadb(server):
        write_mariadb_parameter_file(server, mariadb_endpoint_host(server))
        command.extend(mariadb_command_arguments(server))
    return command, server.data["dir"]


def get_runtime_requirements(server):
    """Return Docker runtime metadata for TeamSpeak 3."""

    requirements = {
        "engine": "docker",
        "family": "service-console",
    }
    if "dir" in server.data:
        requirements["mounts"] = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
        ]
    ports = []
    if "port" in server.data:
        ports.append(
            {
                "host": int(server.data["port"]),
                "container": int(server.data["port"]),
                "protocol": "udp",
            }
        )
    if "queryport" in server.data:
        ports.append(
            {
                "host": int(server.data["queryport"]),
                "container": int(server.data["queryport"]),
                "protocol": "tcp",
            }
        )
    if "filetransferport" in server.data:
        ports.append(
            {
                "host": int(server.data["filetransferport"]),
                "container": int(server.data["filetransferport"]),
                "protocol": "tcp",
            }
        )
    if ports:
        requirements["ports"] = ports
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for TeamSpeak 3."""

    cmd, _cwd = get_start_command(server)
    requirements = get_runtime_requirements(server)
    spec = {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": cmd,
    }
    if _uses_managed_database(server):
        spec["network_mode"] = database_network_name(server)
    if _uses_mariadb(server):
        # TeamSpeak 3.12 loads libmariadb.so.2 from its own redist directory.
        env = dict(server.data.get("env") or {})
        current = env.get("LD_LIBRARY_PATH", "")
        redist = "/srv/server/redist"
        if redist not in current.split(":"):
            env["LD_LIBRARY_PATH"] = redist if not current else current + ":" + redist
        env.setdefault("LANG", "C.UTF-8")
        spec["env"] = env
    return spec


def prestart(server, *_args, **_kwargs):
    """Start a managed MariaDB sidecar before a MariaDB-backed server."""

    if not _uses_mariadb(server):
        return
    if _uses_managed_database(server):
        _ensure_managed_database(server)
    write_mariadb_parameter_file(server, mariadb_endpoint_host(server))


def _uses_mariadb(server):
    return str(server.data.get("db_mode", "sqlite")).strip().lower() == "mariadb"


def _uses_managed_database(server):
    if not _uses_mariadb(server):
        return False
    host = str(server.data.get("db_host", "")).strip().lower()
    return host in ("", "managed")


def _safe_name(server):
    return re.sub(r"[^a-z0-9_.-]", "-", str(server.name).lower()).strip("-") or "server"


def database_network_name(server):
    """Return the private Docker network shared by TeamSpeak and MariaDB."""

    return "alphagsm-ts3-" + _safe_name(server)


def database_container_name(server):
    """Return the managed MariaDB container name."""

    return "alphagsm-ts3-db-" + _safe_name(server)


def database_data_dir(server):
    """Return the host directory that stores the MariaDB data directory."""

    return os.path.join(server.data["dir"], ".alphagsm", "mariadb-data")


def mariadb_endpoint_host(server):
    """Return the hostname TeamSpeak should use for MariaDB."""

    host = str(server.data.get("db_host", "")).strip()
    if host and host.lower() != "managed":
        return host
    if str(server.data.get("runtime", "")).strip().lower() == "docker" or _uses_managed_database(server):
        return MANAGED_DB_ALIAS
    return "127.0.0.1"


def mariadb_command_arguments(server):
    """Return TeamSpeak arguments that select the MariaDB plugin."""

    arguments = [
        "dbplugin=ts3db_mariadb",
        "dbsqlpath=sql/",
        "dbsqlcreatepath=create_mariadb/",
        "dbpluginparameter=ts3db_mariadb.ini",
    ]
    licensepath = str(server.data.get("licensepath", "")).strip()
    if licensepath:
        arguments.append("licensepath=%s" % (licensepath,))
    return arguments


def write_mariadb_parameter_file(server, host):
    """Write the MariaDB plugin file without placing the password on the command line."""

    password = str(server.data.get("db_password", ""))
    if not password or any(character in password for character in "\r\n"):
        raise ServerError("MariaDB mode requires a db_password on one line")
    username = str(server.data.get("db_user", "root")).strip() or "root"
    database = str(server.data.get("db_name", "ts3")).strip() or "ts3"
    port = int(server.data.get("db_port", 3306))
    directory = server.data["dir"]
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "ts3db_mariadb.ini")
    body = (
        "[config]\n"
        "host=%s\n"
        "port=%s\n"
        "username=%s\n"
        "password=%s\n"
        "database=%s\n"
        "socket=\n"
    ) % (host, port, username, password, database)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(body)
    os.chmod(path, 0o600)
    return path


def _run_docker(*args, check=True):
    return subprocess.run(
        ["docker", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def _redact(text, secret):
    if not text:
        return ""
    if secret:
        text = text.replace(secret, "[redacted]")
    return text.strip()


def managed_database_run_args(server, *, initialize):
    """Return the docker run arguments for a new managed MariaDB container."""

    password = str(server.data.get("db_password", ""))
    data_dir = database_data_dir(server)
    command = [
        "run", "-d",
        "--name", database_container_name(server),
        "--network", database_network_name(server),
        "--network-alias", MANAGED_DB_ALIAS,
        "--restart", "unless-stopped",
        "-v", "%s:/var/lib/mysql" % (data_dir,),
        "-e", "MARIADB_AUTO_UPGRADE=1",
    ]
    if initialize:
        command.extend([
            "-e", "MYSQL_ROOT_PASSWORD=%s" % (password,),
            "-e", "MYSQL_DATABASE=%s" % (str(server.data.get("db_name", "ts3")),),
        ])
        user = str(server.data.get("db_user", "root")).strip()
        if user and user.lower() != "root":
            command.extend([
                "-e", "MYSQL_USER=%s" % (user,),
                "-e", "MYSQL_PASSWORD=%s" % (password,),
            ])
    command.append(MANAGED_DB_IMAGE)
    return command


def _ensure_managed_database(server):
    """Launch the private MariaDB container and wait until it accepts connections."""

    if shutil.which("docker") is None:
        raise ServerError("Docker is required to launch the managed TeamSpeak MariaDB")
    if str(server.data.get("runtime", "docker")).strip().lower() != "docker":
        raise ServerError("Managed TeamSpeak MariaDB requires the docker runtime, or set db_host to an existing database")
    password = str(server.data.get("db_password", ""))
    network = database_network_name(server)
    container = database_container_name(server)
    inspect_network = _run_docker("network", "inspect", network, check=False)
    if inspect_network.returncode != 0:
        created = _run_docker("network", "create", network, check=False)
        if created.returncode != 0:
            raise ServerError("Could not create the TeamSpeak database network: " + _redact(created.stderr, password))
    data_dir = database_data_dir(server)
    os.makedirs(data_dir, exist_ok=True)
    inspect_container = _run_docker("inspect", container, check=False)
    if inspect_container.returncode != 0:
        initialize = not os.path.isdir(os.path.join(data_dir, "mysql"))
        started = _run_docker(*managed_database_run_args(server, initialize=initialize), check=False)
        if started.returncode != 0:
            raise ServerError("Could not start managed TeamSpeak MariaDB: " + _redact(started.stderr, password))
    else:
        running = _run_docker("inspect", "-f", "{{.State.Running}}", container, check=False)
        if running.returncode != 0 or running.stdout.strip().lower() != "true":
            restarted = _run_docker("start", container, check=False)
            if restarted.returncode != 0:
                raise ServerError("Could not restart managed TeamSpeak MariaDB: " + _redact(restarted.stderr, password))
        _run_docker("network", "connect", "--alias", MANAGED_DB_ALIAS, network, container, check=False)
    deadline = time.monotonic() + 60
    last_detail = ""
    while time.monotonic() < deadline:
        ready = _run_docker(
            "exec", container, "mariadb-admin", "--user=root", "--password=%s" % (password,),
            "--host=127.0.0.1", "ping", "--silent",
            check=False,
        )
        if ready.returncode == 0:
            return
        last_detail = _redact(ready.stderr or ready.stdout, password)
        time.sleep(1)
    raise ServerError("Managed TeamSpeak MariaDB did not become ready: " + last_detail)


def get_query_address(server):
    """Return the TS3 ServerQuery address used to query the TeamSpeak 3 server.

    TeamSpeak 3 exposes a TCP ServerQuery interface on ``queryport``
    (default 10011).  Using the ``"ts3"`` protocol allows AlphaGSM to retrieve
    real server information (name, client count, channel list) via the TS3
    ServerQuery protocol rather than a plain TCP ping.
    """
    return (runtime_module.resolve_query_host(server), int(server.data.get("queryport", "10011")), "ts3")


def get_info_address(server):
    """Return the TS3 ServerQuery address used by the ``info`` command."""
    return (runtime_module.resolve_query_host(server), int(server.data.get("queryport", "10011")), "ts3")


def do_stop(server, j):
    """Send the standard stop command to TeamSpeak 3."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed TeamSpeak 3 status is not implemented yet."""


def message(server, msg):
    """TeamSpeak 3 has no generic user message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a TeamSpeak 3 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def get_query_credentials(server):
    """Return TS3 ServerQuery admin credentials as (username, password) or None.

    Checks for the ``serverquery_admin_password.txt`` file written by
    TeamSpeak 3 server 3.13.3+ on first run, then falls back to parsing the
    admin password from the selected runtime's log. Recovered credentials are
    retained privately so container recreation does not lose them.
    """
    server_dir = pathlib.Path(server.data["dir"])
    # TS3 3.13.3+ writes the admin password to this file on first run.
    pw_file = server_dir / "serverquery_admin_password.txt"
    if pw_file.exists():
        password = pw_file.read_text(errors="replace").strip()
        if password:
            return ("serveradmin", password)

    # Fallback: parse the active runtime log for the TS3 admin password line.
    # TS3 prints: loginname= "serveradmin", password= "<pw>" on first startup.
    try:
        log_text = runtime_module.read_server_logs(server, lines=None)
    except (OSError, runtime_module.RuntimeError):
        return None
    match = re.search(r'loginname= "serveradmin", password= "([^"]+)"', log_text)
    if not match:
        return None
    password = match.group(1)
    try:
        # Exclusive creation never overwrites an operator's credential file
        # or follows an existing symlink. Keep the secret out of CLI output.
        descriptor = os.open(pw_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(password + "\n")
    except OSError:
        pass
    return ("serveradmin", password)


def checkvalue(server, key, *value):
    """Validate supported TeamSpeak 3 datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport", "filetransferport", "db_port"):
        return int(value[0])
    if key[0] in ("exe_name", "dir", "url", "version", "db_name", "db_user", "db_password", "db_host", "licensepath"):
        return str(value[0])
    if key[0] == "db_mode":
        mode = str(value[0]).strip().lower()
        if mode not in ("sqlite", "mariadb"):
            raise ServerError("db_mode must be sqlite or mariadb")
        return mode
    if key[0] == "license_accepted":
        return str(value[0]).lower() in ("1", "true", "yes", "on")
    raise ServerError("Unsupported key")
