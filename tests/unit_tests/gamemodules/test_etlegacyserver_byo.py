"""ET: Legacy owned multiplayer pak import."""

import os
from types import SimpleNamespace

import pytest

from gamemodules import etlegacyserver
from server import ServerError
from utils.asset_import import import_assets
from utils.byo_files import inspect_files


STOCK_PAKS = (
    "etmain/pak0.pk3",
    "etmain/pak1.pk3",
    "etmain/pak2.pk3",
)


def _server(tmp_path):
    return SimpleNamespace(name="etl", data={"dir": str(tmp_path)})


def _recipe(tmp_path):
    return etlegacyserver.get_asset_requirements(_server(tmp_path))


def _write_tree(root, names, payload=b"owned-pak"):
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload + b"-" + name.encode("utf-8"))


def test_recipe_requires_the_stock_multiplayer_pak_set(tmp_path):
    recipe = _recipe(tmp_path)

    assert recipe["include"] == list(STOCK_PAKS)
    assert recipe["required"] == list(STOCK_PAKS)
    assert [item["path"] for item in recipe["requirements"]] == list(STOCK_PAKS)
    assert all(source["kind"] != "steamcmd" for source in recipe["sources"])
    assert "multiplayer_maps" not in recipe


def test_managed_import_keeps_stock_paks_and_drops_other_files(tmp_path):
    source = tmp_path / "owned"
    target = tmp_path / "server"
    _write_tree(
        source,
        (
            *STOCK_PAKS,
            "ET.exe",
            "etmain/etded.exe",
            "etmain/video/etintro.roq",
            "etmain/pak3.pk3",
        ),
    )

    report = import_assets(source, target, _recipe(target))

    assert report["copied"] == list(STOCK_PAKS)
    for name in STOCK_PAKS:
        assert (target / name).is_file()
    assert not (target / "ET.exe").exists()
    assert not (target / "etmain" / "etded.exe").exists()
    assert not (target / "etmain" / "video" / "etintro.roq").exists()
    assert not (target / "etmain" / "pak3.pk3").exists()
    assert inspect_files(target, _recipe(target))["ready"]


def test_managed_import_rejects_a_sentinel_only_tree(tmp_path):
    source = tmp_path / "owned"
    target = tmp_path / "server"
    _write_tree(source, ("etmain/pak0.pk3", "etmain/readme.txt"))

    with pytest.raises(ServerError, match="pak1.pk3"):
        import_assets(source, target, _recipe(target))

    assert not (target / "etmain" / "pak0.pk3").exists()


def test_file_check_rejects_a_sentinel_only_tree(tmp_path):
    root = tmp_path / "server"
    _write_tree(root, ("etmain/pak0.pk3",))

    report = inspect_files(root, _recipe(root))

    assert report["ready"] is False
    assert report["missing"] == ["etmain/pak1.pk3", "etmain/pak2.pk3"]


def test_start_rejects_a_sentinel_only_install(tmp_path):
    (tmp_path / "etlded.x86_64").write_text("", encoding="utf-8")
    (tmp_path / "etmain").mkdir()
    (tmp_path / "etmain" / "pak0.pk3").write_text("", encoding="utf-8")
    server = _server(tmp_path)
    server.data.update(
        {
            "exe_name": "etlded.x86_64",
            "fs_game": "legacy",
            "hostname": "AlphaGSM etl",
            "configfile": "etl_server.cfg",
            "port": 27960,
        }
    )

    with pytest.raises(ServerError, match="pak1.pk3"):
        etlegacyserver.get_start_command(server)


def test_install_stages_only_stock_paks_from_the_official_freeware_archive(tmp_path, monkeypatch):
    install_dir = tmp_path / "server"
    install_dir.mkdir()
    (install_dir / "etl_server.cfg").write_text("// keep the engine config\n", encoding="utf-8")
    server = _server(install_dir)
    server.data.update(
        {
            "url": "https://www.etlegacy.com/download/file/785",
            "download_name": "etlegacy-v2.86.2-x86_64.tar.gz",
            "exe_name": "etlded.x86_64",
            "hostname": "AlphaGSM etl",
            "configfile": "etl_server.cfg",
            "port": 27960,
            "fs_game": "legacy",
        }
    )
    download_dir = tmp_path / "cache"
    download_dir.mkdir()
    (download_dir / "et260b.x86_full.zip").write_bytes(b"zip")
    (download_dir / "et260b.x86_keygen_V03.run").write_bytes(b"installer")
    seen = {}

    def fake_getpath(module, args):
        seen["module"] = module
        seen["args"] = args
        return str(download_dir)

    def fake_run(cmd, check, stdout, stderr, **_kwargs):
        del check, stdout, stderr
        assert cmd[0] == "sh"
        assert "--nox11" in cmd
        assert "--noexec" in cmd
        target = cmd[cmd.index("--target") + 1]
        etmain = os.path.join(target, "etmain")
        os.makedirs(os.path.join(etmain, "video"), exist_ok=True)
        os.makedirs(os.path.join(target, "pb"), exist_ok=True)
        os.makedirs(os.path.join(target, "bin"), exist_ok=True)
        for name in ("pak0.pk3", "pak1.pk3", "pak2.pk3"):
            with open(os.path.join(etmain, name), "wb") as handle:
                handle.write(b"stock-" + name.encode("ascii"))
        with open(os.path.join(etmain, "mp_bin.pk3"), "wb") as handle:
            handle.write(b"engine-binaries")
        with open(os.path.join(etmain, "server.cfg"), "wb") as handle:
            handle.write(b"stock-cfg")
        with open(os.path.join(etmain, "video", "etintro.roq"), "wb") as handle:
            handle.write(b"client-video")
        with open(os.path.join(target, "pb", "pbcl.so"), "wb") as handle:
            handle.write(b"punkbuster")
        with open(os.path.join(target, "bin", "et.x86"), "wb") as handle:
            handle.write(b"client-binary")
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(etlegacyserver, "install_archive", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(etlegacyserver.downloader, "getpath", fake_getpath)
    monkeypatch.setattr(etlegacyserver.sp, "run", fake_run)

    etlegacyserver.install(server)

    assert seen["module"] == "url"
    assert seen["args"][0] == "https://cdn.splashdamage.com/downloads/games/wet/et260b.x86_full.zip"
    assert seen["args"][1] == "et260b.x86_full.zip"
    assert seen["args"][2] == "zip"
    etmain = install_dir / "etmain"
    for name in ("pak0.pk3", "pak1.pk3", "pak2.pk3"):
        assert (etmain / name).read_bytes() == b"stock-" + name.encode("ascii")
    assert not (etmain / "mp_bin.pk3").exists()
    assert not (etmain / "server.cfg").exists()
    assert not (etmain / "video").exists()
    assert not (install_dir / "pb").exists()
    assert not (install_dir / "bin").exists()
    assert (install_dir / "etl_server.cfg").read_text(encoding="utf-8") == "// keep the engine config\n"


def test_install_rejects_a_pak0_only_official_payload(tmp_path, monkeypatch):
    install_dir = tmp_path / "server"
    install_dir.mkdir()
    server = _server(install_dir)
    server.data.update(
        {
            "url": "https://www.etlegacy.com/download/file/785",
            "download_name": "etlegacy.tar.gz",
            "exe_name": "etlded.x86_64",
            "configfile": "etl_server.cfg",
            "port": 27960,
            "fs_game": "legacy",
        }
    )
    download_dir = tmp_path / "cache"
    download_dir.mkdir()
    (download_dir / "et260b.x86_keygen_V03.run").write_bytes(b"installer")

    def fake_run(cmd, check, stdout, stderr, **_kwargs):
        del check, stdout, stderr
        target = cmd[cmd.index("--target") + 1]
        etmain = os.path.join(target, "etmain")
        os.makedirs(etmain, exist_ok=True)
        with open(os.path.join(etmain, "pak0.pk3"), "wb") as handle:
            handle.write(b"only-pak0")
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(etlegacyserver, "install_archive", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(etlegacyserver.downloader, "getpath", lambda *_args, **_kwargs: str(download_dir))
    monkeypatch.setattr(etlegacyserver.sp, "run", fake_run)

    with pytest.raises(ServerError, match="pak1.pk3"):
        etlegacyserver.install(server)

    assert not (install_dir / "etmain" / "pak0.pk3").exists()


def test_start_accepts_the_stock_multiplayer_pak_set(tmp_path):
    (tmp_path / "etlded.x86_64").write_text("", encoding="utf-8")
    etmain = tmp_path / "etmain"
    etmain.mkdir()
    for name in ("pak0.pk3", "pak1.pk3", "pak2.pk3"):
        (etmain / name).write_text("", encoding="utf-8")
    server = _server(tmp_path)
    server.data.update(
        {
            "exe_name": "etlded.x86_64",
            "fs_game": "legacy",
            "hostname": "AlphaGSM etl",
            "configfile": "etl_server.cfg",
            "port": 27960,
        }
    )

    cmd, cwd = etlegacyserver.get_start_command(server)

    assert cmd[0] == "./etlded.x86_64"
    assert cwd == server.data["dir"]
