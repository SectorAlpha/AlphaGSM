"""Life is Feudal: Your Own dedicated server lifecycle helpers."""

import getpass
import os
import re
import shutil
import socket
import subprocess
import time

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 320850
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Life is Feudal server",
    "The directory to install Life is Feudal in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Life is Feudal dedicated server to the latest version.",
    "Restart the Life is Feudal dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("db_host", "db_port", "db_name", "db_user", "db_password")
setting_schema = {
    "db_mode": SettingSpec(
        canonical_key="db_mode",
        aliases=("dbmode", "databasemode"),
        description="Whether Life is Feudal should use a locally managed database or an AlphaGSM-managed Docker MariaDB.",
        value_type="string",
        examples=("local", "docker"),
    ),
    "db_host": SettingSpec(
        canonical_key="db_host",
        aliases=("dbhost", "databasehost", "mysqlhost", "mariadbhost"),
        description="Hostname or IP address for the Life is Feudal MySQL/MariaDB service.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        examples=("127.0.0.1", "db.internal"),
    ),
    "db_port": SettingSpec(
        canonical_key="db_port",
        aliases=("dbport", "databaseport", "mysqlport", "mariadbport"),
        description="TCP port for the Life is Feudal MySQL/MariaDB service.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        examples=("3306",),
    ),
    "db_name": SettingSpec(
        canonical_key="db_name",
        aliases=("dbname", "database", "databasename"),
        description="Database/schema name used by Life is Feudal.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        examples=("lif_1",),
    ),
    "db_user": SettingSpec(
        canonical_key="db_user",
        aliases=("dbuser", "databaseuser", "mysqluser", "mariadbuser"),
        description="Database login used by Life is Feudal.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        examples=("root", "lif_server"),
    ),
    "db_password": SettingSpec(
        canonical_key="db_password",
        aliases=("dbpassword", "databasepassword", "mysqlpassword", "mariadbpassword"),
        description="Database password used by Life is Feudal.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        secret=True,
    ),
}

_MANAGED_CONFIG_FOOTER = """

// Managed by AlphaGSM when no upstream docs/config_local.cs template is present.
$DatabaseAddress = "{db_address}";
$DatabaseName = "{db_name}";
$DatabaseUser = "{db_user}";
$DatabasePassword = "{db_password}";
$rootPassword = "{db_password}";
""".lstrip()
_MANAGED_DB_IMAGE = "mariadb:10.3"


def configure(server, ask, port=None, dir=None, *, exe_name="ddctd_cm_yo_server.exe"):
    """Collect and store configuration values for a Life is Feudal server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "28001",
            "rconport": "28002",
            "db_mode": "local",
            "db_host": "127.0.0.1",
            "db_port": 3306,
            "db_name": "lif_1",
            "db_user": "root",
            "db_password": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["config", "sql", "logs"],
        targets=["config", "sql", "logs"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=28000,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Life is Feudal server:",
    )
    _configure_database(server, ask)
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=lambda server: sync_server_config(server),
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Life is Feudal server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=lambda server: sync_server_config(server),
    download_kwargs={"force_windows": IS_LINUX},
)

restart = gamemodule_common.make_restart_hook()

def _configure_database(server, ask):
    """Collect BYO database settings during ``setup``."""

    if ask:
        current_mode = _normalize_db_mode(server.data.get("db_mode", "local"))
        entered_mode = input(
            f"Database mode for Life is Feudal (local/docker) [{current_mode}] "
        ).strip()
        if entered_mode:
            server.data["db_mode"] = _normalize_db_mode(entered_mode)

    prompts = (
        ("db_host", "MySQL/MariaDB host for Life is Feudal", False),
        ("db_port", "MySQL/MariaDB port for Life is Feudal", False),
        ("db_name", "Database/schema name for Life is Feudal", False),
        ("db_user", "Database user for Life is Feudal", False),
        ("db_password", "Database password for Life is Feudal", True),
    )
    for key, prompt, secret in prompts:
        current = server.data.get(key, "")
        if not ask:
            continue
        if secret:
            placeholder = "<stored>" if current else "<blank>"
            entered = getpass.getpass(f"{prompt} [{placeholder}] ").strip()
        else:
            entered = input(f"{prompt} [{current}] ").strip()
        if entered:
            server.data[key] = int(entered) if key == "db_port" else entered


def _normalize_db_mode(value):
    value = str(value or "local").strip().lower()
    if value in {"docker", "managed", "managed-docker", "managed_docker"}:
        return "docker"
    if value in {"local", "host"}:
        return "local"
    raise ServerError("db_mode must be either 'local' or 'docker'")


def _config_local_path(server):
    return os.path.join(server.data["dir"], "config_local.cs")


def _docs_config_local_path(server):
    return os.path.join(server.data["dir"], "docs", "config_local.cs")


def _docs_mysql_config_path(server):
    return os.path.join(server.data["dir"], "docs", "my.ini")


def _database_address(server):
    return f'{server.data.get("db_host", "127.0.0.1")}:{int(server.data.get("db_port", 3306))}'


def _managed_db_container_name(server):
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "-", str(server.name))
    return f"alphagsm-lif-db-{safe_name}"


def _managed_db_data_dir(server):
    return os.path.join(server.data["dir"], ".alphagsm", "mariadb-data")


def _managed_db_config_path(server):
    return os.path.join(server.data["dir"], ".alphagsm", "lif-mariadb.cnf")


def _prepare_managed_db_config(server):
    source = _docs_mysql_config_path(server)
    if not os.path.isfile(source):
        return None
    target = _managed_db_config_path(server)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(source, target)
    return target


def _run_docker(*args, check=True, capture_output=True):
    return subprocess.run(
        ["docker", *args],
        check=check,
        capture_output=capture_output,
        text=True,
    )


def _docker_available():
    return shutil.which("docker") is not None


def _docker_container_exists(name):
    result = _run_docker("inspect", name, check=False)
    return result.returncode == 0


def _docker_container_running(name):
    result = _run_docker(
        "inspect",
        "-f",
        "{{.State.Running}}",
        name,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def _managed_database_ready(container_name, password):
    last_detail = ""
    for admin_binary in ("mariadb-admin", "mysqladmin"):
        result = _run_docker(
            "exec",
            container_name,
            admin_binary,
            "--user=root",
            f"--password={password}",
            "--host=127.0.0.1",
            "ping",
            "--silent",
            check=False,
        )
        detail = (result.stderr or result.stdout).strip()
        if result.returncode == 0:
            return True, detail
        last_detail = detail
        if "executable file not found" not in detail.lower():
            return False, detail
    return False, last_detail


def _ensure_managed_root_grants(container_name, password):
    sql_password = str(password).replace("'", "''")
    sql = (
        "CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY '{password}'; "
        "ALTER USER 'root'@'%' IDENTIFIED BY '{password}'; "
        "GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION; "
        "FLUSH PRIVILEGES;"
    ).format(password=sql_password)
    last_detail = ""
    for client_binary in ("mariadb", "mysql"):
        result = _run_docker(
            "exec",
            container_name,
            client_binary,
            "-uroot",
            f"-p{password}",
            "-e",
            sql,
            check=False,
        )
        detail = (result.stderr or result.stdout).strip()
        if result.returncode == 0:
            return
        last_detail = detail
        if "executable file not found" not in detail.lower():
            break
    raise ServerError(
        "Could not grant remote root access inside managed MariaDB container {}: {}".format(
            container_name, last_detail
        )
    )


def _ensure_managed_database(server):
    """Launch or reuse the AlphaGSM-managed MariaDB sidecar for LiF."""

    if not _docker_available():
        gamemodule_common.raise_byo_requirement(
            "lifeisfeudalserver",
            "Docker installed locally so AlphaGSM can launch the managed MariaDB sidecar",
            actions=(
                "Install Docker locally and rerun start, or switch db_mode back to local",
                "If you stay on local mode, provision your own MySQL/MariaDB and keep db_host/db_port pointed at it",
            ),
            docs_slug="lifeisfeudalserver",
        )

    host = str(server.data.get("db_host", "127.0.0.1")).strip() or "127.0.0.1"
    if host not in {"127.0.0.1", "localhost"}:
        raise ServerError(
            "Managed Docker database mode requires db_host to be 127.0.0.1 or localhost"
        )

    password = str(server.data.get("db_password", "")).strip()
    if not password:
        gamemodule_common.raise_byo_requirement(
            "lifeisfeudalserver",
            "a non-empty db_password before AlphaGSM can launch the managed MariaDB sidecar",
            actions=(
                "Run setup interactively or use set db_password <value> before rerunning start",
                "Keep db_name and db_user aligned with the database credentials you want AlphaGSM to manage",
            ),
            docs_slug="lifeisfeudalserver",
        )

    container_name = _managed_db_container_name(server)
    if _docker_container_running(container_name):
        return
    if _docker_container_exists(container_name):
        result = _run_docker("start", container_name, check=False)
        if result.returncode != 0:
            raise ServerError(
                "Could not restart managed MariaDB container {}: {}".format(
                    container_name, (result.stderr or result.stdout).strip()
                )
            )
    else:
        os.makedirs(_managed_db_data_dir(server), exist_ok=True)
        db_user = str(server.data.get("db_user", "root")).strip() or "root"
        db_name = str(server.data.get("db_name", "lif_1")).strip() or "lif_1"
        db_port = int(server.data.get("db_port", 3306))
        config_path = _prepare_managed_db_config(server)
        command = [
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            f"127.0.0.1:{db_port}:3306",
            "-v",
            f"{_managed_db_data_dir(server)}:/var/lib/mysql",
            "-e",
            f"MYSQL_DATABASE={db_name}",
            "-e",
            f"MYSQL_ROOT_PASSWORD={password}",
            "-e",
            "MYSQL_ROOT_HOST=%",
        ]
        if config_path is not None:
            command.extend(
                [
                    "-v",
                    f"{config_path}:/etc/mysql/conf.d/lif-mariadb.cnf:ro",
                ]
            )
        if db_user.lower() != "root":
            command.extend(
                [
                    "-e",
                    f"MYSQL_USER={db_user}",
                    "-e",
                    f"MYSQL_PASSWORD={password}",
                ]
            )
        command.append(_MANAGED_DB_IMAGE)
        result = _run_docker(*command, check=False)
        if result.returncode != 0:
            raise ServerError(
                "Could not start managed MariaDB container {}: {}".format(
                    container_name, (result.stderr or result.stdout).strip()
                )
            )

    deadline = time.time() + 90
    last_error = None
    while time.time() < deadline:
        ready, detail = _managed_database_ready(container_name, password)
        if ready:
            _ensure_managed_root_grants(container_name, password)
            return
        last_error = detail or "database bootstrap still in progress"
        time.sleep(1)
    raise ServerError(
        "Managed MariaDB container {} did not become SQL-ready on {}:{}: {}".format(
            container_name,
            host,
            int(server.data.get("db_port", 3306)),
            last_error or "connection timed out",
        )
    )


def _replace_named_config_value(text, names, value):
    """Replace quoted assignment values for known config_local.cs field names."""

    total_matches = 0
    for name in names:
        pattern = re.compile(
            rf'(^\s*[^=\n]*\b{re.escape(name)}\b[^=\n]*=\s*")([^"\n\r]*)(".*$)',
            re.MULTILINE,
        )
        text, matches = pattern.subn(
            lambda match: f'{match.group(1)}{value}{match.group(3)}',
            text,
        )
        total_matches += matches
    return text, total_matches


def sync_server_config(server):
    """Write or refresh the Life is Feudal database config_local.cs file."""

    target_path = _config_local_path(server)
    source_path = _docs_config_local_path(server)
    if os.path.isfile(target_path):
        with open(target_path, "r", encoding="utf-8") as handle:
            text = handle.read()
    elif os.path.isfile(source_path):
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.copyfile(source_path, target_path)
        with open(target_path, "r", encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = _MANAGED_CONFIG_FOOTER

    replacements = {
        ("DatabaseAddress", "databaseAddress", "Server", "server"): _database_address(server),
        ("DatabaseName", "databaseName", "DBName", "dbName"): str(server.data.get("db_name", "lif_1")),
        ("DatabaseUser", "databaseUser", "DBUser", "dbUser", "UserName", "user"): str(server.data.get("db_user", "root")),
        ("DatabasePassword", "databasePassword", "DBPassword", "dbPassword", "rootPassword", "password"): str(
            server.data.get("db_password", "")
        ),
    }

    total_matches = 0
    for names, replacement in replacements.items():
        text, matches = _replace_named_config_value(text, names, replacement)
        total_matches += matches

    if total_matches == 0 and "Managed by AlphaGSM" not in text:
        text = text.rstrip() + "\n\n" + _MANAGED_CONFIG_FOOTER

    os.makedirs(server.data["dir"], exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as handle:
        handle.write(
            text.format(
                db_address=_database_address(server),
                db_name=str(server.data.get("db_name", "lif_1")),
                db_user=str(server.data.get("db_user", "root")),
                db_password=str(server.data.get("db_password", "")),
            )
        )


def _assert_database_endpoint_available(server):
    """Require the configured MySQL/MariaDB service before launch."""

    host = str(server.data.get("db_host", "127.0.0.1"))
    port = int(server.data.get("db_port", 3306))
    try:
        conn = socket.create_connection((host, port), timeout=1.0)
    except OSError:
        gamemodule_common.raise_byo_requirement(
            "lifeisfeudalserver",
            f"a reachable MySQL/MariaDB service for {host}:{port} plus matching config_local.cs database settings",
            actions=(
                "Run setup interactively or use set db_host/db_port/db_name/db_user/db_password so AlphaGSM records the right database details",
                "Provision MySQL/MariaDB locally or publish a Dockerized database to that host and port before rerunning start",
                "Keep the database service running while AlphaGSM launches and manages the server",
            ),
            docs_slug="lifeisfeudalserver",
        )
    else:
        conn.close()


def prestart(server):
    """Sync config and ensure the chosen database mode is ready."""

    sync_server_config(server)
    if _normalize_db_mode(server.data.get("db_mode", "local")) == "docker":
        _ensure_managed_database(server)
    _assert_database_endpoint_available(server)


def get_start_command(server):
    """Build the command used to launch a Life is Feudal dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [server.data["exe_name"]]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Life is Feudal using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed Life is Feudal status is not implemented yet."


def message(server, msg):
    """Life is Feudal has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Life is Feudal server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Life is Feudal datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_handlers={"db_mode": lambda _server, raw: _normalize_db_mode(raw)},
        resolved_int_keys=("db_port",),
        resolved_str_keys=("db_host", "db_name", "db_user", "db_password"),
        raw_int_keys=("port", "queryport", "rconport"),
        raw_str_keys=("exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'rconport', 'protocol': 'udp'}, {'key': 'rconport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'rconport', 'protocol': 'udp'}, {'key': 'rconport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
