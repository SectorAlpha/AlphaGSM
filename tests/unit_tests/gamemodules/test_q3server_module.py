import os
import zipfile

import pytest

from utils import archive_install

import gamemodules.q3server as q3server


class DummyData(dict):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def save(self):
        self.saved += 1


class DummyServer:
    def __init__(self, name="alpha"):
        self.name = name
        self.data = DummyData()


def test_q3server_configure_sets_expected_defaults(tmp_path):
    server = DummyServer("q3")

    q3server.configure(server, ask=False, port=27960, dir=str(tmp_path), url="http://example.com/q3.tar.gz")

    assert server.data["fs_game"] == "baseq3"
    assert server.data["startmap"] == "q3dm17"


def test_q3server_resolve_download_uses_ioquake3_linux_zip():
    version, url = q3server.resolve_download()

    assert version == "linux"
    assert url == "https://files.ioquake3.org/Linux.zip"


def test_q3server_get_start_command_builds_expected_args(tmp_path):
    server = DummyServer("q3")
    exe = tmp_path / "ioq3ded.x86_64"
    exe.write_text("")
    (tmp_path / "baseq3").mkdir()
    (tmp_path / "baseq3" / "pak0.pk3").write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ioq3ded.x86_64",
            "fs_game": "baseq3",
            "hostname": "AlphaGSM q3",
            "port": 27960,
            "startmap": "q3dm17",
        }
    )

    cmd, cwd = q3server.get_start_command(server)

    assert cmd[0] == "./ioq3ded.x86_64"
    assert "net_port" in cmd
    assert cwd == server.data["dir"]


def test_q3server_runtime_requirements_use_quake_linux_family(tmp_path):
    (tmp_path / "ioq3ded.x86_64").write_text("")
    (tmp_path / "baseq3").mkdir()
    (tmp_path / "baseq3" / "pak0.pk3").write_text("")
    server = DummyServer("q3")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ioq3ded.x86_64",
            "fs_game": "baseq3",
            "hostname": "AlphaGSM q3",
            "port": 27960,
            "startmap": "q3dm17",
        }
    )

    requirements = q3server.get_runtime_requirements(server)
    spec = q3server.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "quake-linux"
    assert requirements["ports"] == [
        {"host": 27960, "container": 27960, "protocol": "udp"}
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][0] == "./ioq3ded.x86_64"


@pytest.mark.parametrize(
    "exe_name",
    ["ioq3ded.x86_64", "ioquake3.x86_64", "./ioquake3.x86_64", "baseq3/cgamex86_64.so"],
)
def test_q3server_install_keeps_dedicated_code_and_all_content(
    tmp_path, monkeypatch, exe_name
):
    stage_root = tmp_path / "download"
    source = stage_root / "Linux"
    client_paths = {
        "ioquake3.x86_64",
        "renderer_opengl1_x86_64.so",
        "renderer_opengl2_x86_64.so",
        "baseq3/cgamex86_64.so",
        "baseq3/uix86_64.so",
        "baseq3/vm/cgame.qvm",
        "baseq3/vm/ui.qvm",
        "missionpack/cgamex86_64.so",
        "missionpack/uix86_64.so",
        "missionpack/vm/cgame.qvm",
        "missionpack/vm/ui.qvm",
    }
    server_paths = {
        "ioq3ded.x86_64",
        "baseq3/qagamex86_64.so",
        "baseq3/vm/qagame.qvm",
        "missionpack/qagamex86_64.so",
        "missionpack/vm/qagame.qvm",
        "baseq3/maps/q3dm6.bsp",
        "baseq3/maps/q3dm17.bsp",
        "missionpack/maps/q3ctf1.bsp",
        "baseq3/scripts/rotation.cfg",
        "libsupport.so",
        "README.txt",
        "custom/cgamex86_64.so",
    }
    payload = {path: path.encode() for path in client_paths | server_paths}
    for relative_path, content in payload.items():
        path = source / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    pk3_paths = [f"baseq3/pak{index}.pk3" for index in range(9)]
    pk3_paths.append("missionpack/pak0.pk3")
    for relative_path in pk3_paths:
        with zipfile.ZipFile(source / relative_path, "w") as archive:
            archive.writestr("maps/q3dm6.bsp", "first map")
            archive.writestr("maps/q3dm17.bsp", "second map")
            archive.writestr("vm/cgame.qvm", "client VM served to players")
        payload[relative_path] = (source / relative_path).read_bytes()
    (stage_root / "Linux.zip").write_text("download archive")
    install_dir = tmp_path / "install"
    install_dir.mkdir()
    (install_dir / "operator.cfg").write_text("operator configuration")
    server = DummyServer("q3")
    q3server.configure(server, ask=False, port=27960, dir=str(install_dir))
    server.data["exe_name"] = exe_name
    monkeypatch.setattr(q3server, "install_archive", archive_install.install_archive)
    monkeypatch.setattr(q3server, "detect_compression", archive_install.detect_compression)
    monkeypatch.setattr(
        archive_install.downloader, "getpath", lambda module, args: str(stage_root)
    )

    q3server.install(server)

    chosen_path = os.path.normpath(exe_name)
    for relative_path, content in payload.items():
        assert (source / relative_path).read_bytes() == content
        if relative_path in client_paths and relative_path != chosen_path:
            assert not (install_dir / relative_path).exists(), relative_path
        else:
            assert (install_dir / relative_path).read_bytes() == content
    assert not (install_dir / "Linux.zip").exists()
    assert (install_dir / "operator.cfg").read_text() == "operator configuration"
    assert (install_dir / exe_name).stat().st_mode & 0o111
    command, cwd = q3server.get_start_command(server)
    assert command[0] == "./" + exe_name
    assert cwd == server.data["dir"]
