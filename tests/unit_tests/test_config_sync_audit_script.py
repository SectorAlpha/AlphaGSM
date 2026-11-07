from pathlib import Path
import io
import runpy
from contextlib import redirect_stdout


def _load_script_namespace():
    script_path = Path("scripts/list_missing_config_sync_contracts.py")
    return runpy.run_path(str(script_path), run_name="config_sync_audit_script_test")


def test_scan_reports_modules_missing_config_sync_contract(tmp_path):
    repo_root = tmp_path
    gm_root = repo_root / "src" / "gamemodules"
    gm_root.mkdir(parents=True)

    (gm_root / "missing_sync_keys.py").write_text(
        """
def sync_server_config(server):
    return None
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (gm_root / "managed_config_without_keys.py").write_text(
        """
def checkvalue(server, key, *values, **kwargs):
    return values[0]

def write_example(server):
    server.data.setdefault("configfile", "server.cfg")
    payload = {"port": 1, "servername": "Example"}
    return json.dump(payload, open("server.json", "w", encoding="utf-8"))
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (gm_root / "complete_module.py").write_text(
        """
config_sync_keys = ("port",)

def sync_server_config(server):
    return None
""".strip()
        + "\n",
        encoding="utf-8",
    )

    namespace = _load_script_namespace()

    findings = namespace["scan"](repo_root)

    assert findings == [
        {
            "path": "src/gamemodules/managed_config_without_keys.py",
            "reason": "manages real server config but missing config_sync_keys",
        },
        {
            "path": "src/gamemodules/missing_sync_keys.py",
            "reason": "missing config_sync_keys for sync_server_config",
        },
    ]


def test_main_prints_human_readable_report(tmp_path):
    repo_root = tmp_path
    gm_root = repo_root / "src" / "gamemodules"
    gm_root.mkdir(parents=True)
    (gm_root / "missing_sync_keys.py").write_text(
        """
def sync_server_config(server):
    return None
""".strip()
        + "\n",
        encoding="utf-8",
    )

    namespace = _load_script_namespace()
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = namespace["main"]([], repo_root=repo_root)

    assert exit_code == 0
    assert stdout.getvalue().splitlines() == [
        "Found 1 modules missing config-sync contract coverage.",
        "src/gamemodules/missing_sync_keys.py - missing config_sync_keys for sync_server_config",
    ]
