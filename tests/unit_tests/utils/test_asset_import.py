"""Portable owned-asset staging uses allowlists and preserves operator data."""

import json
import os
from pathlib import Path
import stat
import tarfile
import zipfile

import pytest

from server import ServerError
from utils import asset_import


RECIPE = {
    "roots": ("", "game"),
    "include": ("halo3/*.dll", "halo3/maps/*.map"),
    "required": ("halo3/halo3.dll", "halo3/maps/shared.map"),
    "target": "game",
}


def write_tree(root, *, dll="engine", map_data="maps"):
    """Create a small owned asset installation with unrelated operator state."""
    (root / "halo3/maps").mkdir(parents=True)
    (root / "halo3/halo3.dll").write_text(dll)
    (root / "halo3/maps/shared.map").write_text(map_data)
    (root / "settings.json").write_text("private settings")
    (root / "save.dat").write_text("private save")
    return root


def _make_symlink(link, target):
    """Exercise links when the host grants symlink creation privileges."""
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip("Host cannot create directory symlinks: %s" % error)


def test_directory_import_records_owned_files_and_skips_repeat(tmp_path):
    source = write_tree(tmp_path / "owned game")
    destination = tmp_path / "server"

    report = asset_import.import_assets(source, destination, RECIPE)

    assert report["status"] == "ready"
    assert report["copied"] == ["game/halo3/halo3.dll", "game/halo3/maps/shared.map"]
    assert not (destination / "game/settings.json").exists()
    assert not (destination / "game/save.dat").exists()
    assert (destination / "game/halo3/halo3.dll").read_text() == "engine"
    manifest = json.loads((destination / ".alphagsm/assets.json").read_text())
    assert len(manifest["files"]["game/halo3/halo3.dll"]["sha256"]) == 64
    before = (destination / "game/halo3/halo3.dll").stat().st_mtime_ns

    repeat = asset_import.import_assets(source, destination, RECIPE)

    assert repeat["copied"] == []
    assert repeat["skipped"] == report["copied"]
    assert (destination / "game/halo3/halo3.dll").stat().st_mtime_ns == before
    assert asset_import.check_assets(destination, RECIPE)["ready"]
    json.dumps(report)


def test_import_updates_owned_unchanged_files_and_keeps_other_content(tmp_path):
    source = write_tree(tmp_path / "owned")
    destination = tmp_path / "server"
    asset_import.import_assets(source, destination, RECIPE)
    (destination / "game/operator.txt").write_text("keep")
    (source / "halo3/halo3.dll").write_text("updated engine")

    report = asset_import.import_assets(source, destination, RECIPE)

    assert report["copied"] == ["game/halo3/halo3.dll"]
    assert (destination / "game/halo3/halo3.dll").read_text() == "updated engine"
    assert (destination / "game/operator.txt").read_text() == "keep"


@pytest.mark.parametrize("existing", ["unrelated", "modified"])
def test_import_refuses_unowned_or_modified_destination_files(tmp_path, existing):
    source = write_tree(tmp_path / "owned")
    destination = tmp_path / "server"
    if existing == "modified":
        asset_import.import_assets(source, destination, RECIPE)
    else:
        (destination / "game/halo3").mkdir(parents=True)
    (destination / "game/halo3/halo3.dll").write_text("operator file")

    with pytest.raises(ServerError, match="unrelated|modified|owned"):
        asset_import.import_assets(source, destination, RECIPE)

    assert (destination / "game/halo3/halo3.dll").read_text() == "operator file"


@pytest.mark.parametrize("archive_format", ["zip", "tar", "tar.gz", "tar.bz2", "tar.xz"])
def test_import_accepts_archive_wrapper_and_recipe_root(tmp_path, archive_format):
    source = write_tree(tmp_path / "owned")
    archive = tmp_path / ("assets." + archive_format)
    if archive_format == "zip":
        with zipfile.ZipFile(archive, "w") as bundle:
            for path in source.rglob("*"):
                if path.is_file():
                    bundle.write(path, "export/game/" + path.relative_to(source).as_posix())
    else:
        mode = "w" if archive_format == "tar" else "w:" + archive_format.split(".")[1]
        with tarfile.open(archive, mode) as bundle:
            bundle.add(source, arcname="export/game")

    report = asset_import.import_assets(archive, tmp_path / "server", RECIPE)

    assert len(report["copied"]) == 2
    assert (tmp_path / "server/game/halo3/maps/shared.map").read_text() == "maps"


def test_import_detects_ambiguous_roots(tmp_path):
    source = write_tree(tmp_path / "owned")
    write_tree(source / "game")

    with pytest.raises(ServerError, match="[Aa]mbiguous"):
        asset_import.import_assets(source, tmp_path / "server", RECIPE)

    assert not (tmp_path / "server").exists()


@pytest.mark.parametrize("problem", ["missing", "empty"])
def test_required_assets_are_validated_before_destination_mutation(tmp_path, problem):
    source = write_tree(tmp_path / "owned")
    required = source / "halo3/maps/shared.map"
    if problem == "missing":
        required.unlink()
    else:
        required.write_bytes(b"")
    destination = tmp_path / "server"

    with pytest.raises(ServerError, match="shared.map"):
        asset_import.import_assets(source, destination, RECIPE)

    assert not destination.exists()
    report = asset_import.check_assets(destination, RECIPE)
    assert not report["ready"]
    assert "game/halo3/maps/shared.map" in report["missing"]


def test_case_insensitive_recipe_normalizes_selected_paths(tmp_path):
    source = tmp_path / "owned"
    (source / "Halo3/Maps").mkdir(parents=True)
    (source / "Halo3/Halo3.DLL").write_text("engine")
    (source / "Halo3/Maps/Shared.MAP").write_text("maps")

    asset_import.import_assets(source, tmp_path / "server", dict(RECIPE, case_insensitive=True))

    assert (tmp_path / "server/game/halo3/halo3.dll").read_text() == "engine"


@pytest.mark.parametrize("unsafe", ["../escape", "/absolute", "C:/drive", "halo3/CON.dll", "halo3/bad?.dll", "halo3/trailing. ", "halo3\\bad.dll"])
def test_archive_rejects_unsafe_paths(tmp_path, unsafe):
    archive = tmp_path / "assets.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("halo3/halo3.dll", b"engine")
        bundle.writestr("halo3/maps/shared.map", b"maps")
        bundle.writestr(unsafe, b"unsafe")

    with pytest.raises(ServerError, match="[Uu]nsafe|portable"):
        asset_import.import_assets(archive, tmp_path / "server", RECIPE)

    assert not (tmp_path / "server").exists()


def test_archive_rejects_portable_case_collisions(tmp_path):
    archive = tmp_path / "assets.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("halo3/halo3.dll", b"engine")
        bundle.writestr("halo3/HALO3.dll", b"other")
        bundle.writestr("halo3/maps/shared.map", b"maps")

    with pytest.raises(ServerError, match="[Cc]ase|collision"):
        asset_import.import_assets(archive, tmp_path / "server", RECIPE)


@pytest.mark.parametrize("link_format", ["directory", "zip", "tar"])
def test_rejects_links(tmp_path, link_format):
    source = write_tree(tmp_path / "owned")
    if link_format == "directory":
        _make_symlink(source / "linked", source / "halo3")
    elif link_format == "zip":
        source = tmp_path / "assets.zip"
        with zipfile.ZipFile(source, "w") as bundle:
            info = zipfile.ZipInfo("linked")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            bundle.writestr(info, "halo3")
    else:
        source = tmp_path / "assets.tar"
        with tarfile.open(source, "w") as bundle:
            info = tarfile.TarInfo("linked")
            info.type = tarfile.SYMTYPE
            info.linkname = "halo3"
            bundle.addfile(info)

    with pytest.raises(ServerError, match="[Ll]ink"):
        asset_import.import_assets(source, tmp_path / "server", RECIPE)


def test_import_rejects_destination_symlink(tmp_path):
    source = write_tree(tmp_path / "owned")
    outside = tmp_path / "outside"
    outside.mkdir()
    destination = tmp_path / "server"
    destination.mkdir()
    _make_symlink(destination / "game", outside)

    with pytest.raises(ServerError, match="[Ll]ink"):
        asset_import.import_assets(source, destination, RECIPE)

    assert not list(outside.iterdir())


def test_publication_failure_rolls_back_files_and_manifest(tmp_path, monkeypatch):
    source = write_tree(tmp_path / "owned")
    destination = tmp_path / "server"
    asset_import.import_assets(source, destination, RECIPE)
    old_manifest = (destination / ".alphagsm/assets.json").read_bytes()
    (source / "halo3/halo3.dll").write_text("new engine")
    (source / "halo3/maps/shared.map").write_text("new maps")
    real_replace = os.replace
    failed = False

    def fail_second_asset(src, dst):
        nonlocal failed
        if Path(dst).as_posix().endswith("game/halo3/maps/shared.map") and not failed:
            failed = True
            raise OSError("simulated full disk")
        return real_replace(src, dst)

    monkeypatch.setattr(asset_import.os, "replace", fail_second_asset)

    with pytest.raises(ServerError, match="simulated full disk"):
        asset_import.import_assets(source, destination, RECIPE)

    assert (destination / "game/halo3/halo3.dll").read_text() == "engine"
    assert (destination / "game/halo3/maps/shared.map").read_text() == "maps"
    assert (destination / ".alphagsm/assets.json").read_bytes() == old_manifest


def test_export_contains_only_allowlist_and_can_be_imported(tmp_path):
    source = write_tree(tmp_path / "owned")
    output = tmp_path / "transfer.zip"

    report = asset_import.export_assets(source, output, RECIPE)

    assert report["output"] == str(output)
    with zipfile.ZipFile(output) as bundle:
        assert bundle.namelist() == ["halo3/halo3.dll", "halo3/maps/shared.map"]
    asset_import.import_assets(output, tmp_path / "server", RECIPE)
    assert asset_import.check_assets(tmp_path / "server", RECIPE)["ready"]


def test_export_failure_preserves_existing_archive(tmp_path):
    source = write_tree(tmp_path / "owned", map_data="")
    output = tmp_path / "transfer.zip"
    output.write_bytes(b"existing export")

    with pytest.raises(ServerError, match="shared.map"):
        asset_import.export_assets(source, output, RECIPE)

    assert output.read_bytes() == b"existing export"


def test_export_rejects_output_inside_source(tmp_path):
    source = write_tree(tmp_path / "owned")

    with pytest.raises(ServerError, match="[Oo]utput|source"):
        asset_import.export_assets(source, source / "transfer.zip", RECIPE)


def test_tar_rejects_nonregular_payload(tmp_path):
    archive = tmp_path / "assets.tar"
    with tarfile.open(archive, "w") as bundle:
        info = tarfile.TarInfo("fifo")
        info.type = tarfile.FIFOTYPE
        bundle.addfile(info)

    with pytest.raises(ServerError, match="regular|[Uu]nsafe"):
        asset_import.import_assets(archive, tmp_path / "server", RECIPE)


def test_identical_preexisting_files_are_skipped_without_ownership(tmp_path):
    source = write_tree(tmp_path / "owned")
    destination = tmp_path / "server"
    (destination / "game/halo3").mkdir(parents=True)
    (destination / "game/halo3/halo3.dll").write_text("engine")

    report = asset_import.import_assets(source, destination, RECIPE)

    assert report["skipped"] == ["game/halo3/halo3.dll"]
    manifest = json.loads((destination / ".alphagsm/assets.json").read_text())
    assert "game/halo3/halo3.dll" not in manifest["files"]
    assert "game/halo3/maps/shared.map" in manifest["files"]
    (source / "halo3/halo3.dll").write_text("new engine")
    with pytest.raises(ServerError, match="unrelated|unowned"):
        asset_import.import_assets(source, destination, RECIPE)


def test_allowlist_does_not_match_suffix_of_nested_path(tmp_path):
    source = write_tree(tmp_path / "owned")
    (source / "unrelated/halo3").mkdir(parents=True)
    (source / "unrelated/halo3/private.dll").write_text("not allowed")

    report = asset_import.import_assets(source, tmp_path / "server", RECIPE)

    assert report["files"] == ["game/halo3/halo3.dll", "game/halo3/maps/shared.map"]


def test_copy_failure_does_not_publish_partial_assets(tmp_path, monkeypatch):
    source = write_tree(tmp_path / "owned")
    destination = tmp_path / "server"

    def fail_copy(*_args, **_kwargs):
        raise OSError("copy failed")

    monkeypatch.setattr(asset_import.shutil, "copyfileobj", fail_copy)
    with pytest.raises(ServerError, match="copy failed"):
        asset_import.import_assets(source, destination, RECIPE)

    assert not destination.exists()


def test_new_install_publication_failure_leaves_no_files(tmp_path, monkeypatch):
    source = write_tree(tmp_path / "owned")
    destination = tmp_path / "server"
    real_replace = os.replace

    def fail_second_asset(src, dst):
        if Path(dst).as_posix().endswith("game/halo3/maps/shared.map"):
            raise OSError("publication failed")
        return real_replace(src, dst)

    monkeypatch.setattr(asset_import.os, "replace", fail_second_asset)
    with pytest.raises(ServerError, match="publication failed"):
        asset_import.import_assets(source, destination, RECIPE)

    assert not destination.exists()


def test_export_copy_failure_preserves_existing_output(tmp_path, monkeypatch):
    source = write_tree(tmp_path / "owned")
    output = tmp_path / "transfer.zip"
    output.write_bytes(b"old export")

    def fail_copy(*_args, **_kwargs):
        raise OSError("copy failed")

    monkeypatch.setattr(asset_import.shutil, "copyfileobj", fail_copy)
    with pytest.raises(ServerError, match="copy failed"):
        asset_import.export_assets(source, output, RECIPE)

    assert output.read_bytes() == b"old export"


def test_export_rejects_normalized_output_inside_source(tmp_path):
    source = write_tree(tmp_path / "owned")
    (source / "nested").mkdir()

    with pytest.raises(ServerError, match="[Oo]utput|source"):
        asset_import.export_assets(source, source / "nested/../transfer.zip", RECIPE)


def test_export_rejects_output_symlink_ancestor(tmp_path):
    source = write_tree(tmp_path / "owned")
    outside = tmp_path / "outside"
    outside.mkdir()
    _make_symlink(tmp_path / "alias", outside)

    with pytest.raises(ServerError, match="[Ll]ink"):
        asset_import.export_assets(source, tmp_path / "alias/transfer.zip", RECIPE)

    assert not list(outside.iterdir())


def test_install_root_symlink_ancestor_is_rejected(tmp_path):
    source = write_tree(tmp_path / "owned")
    outside = tmp_path / "outside"
    outside.mkdir()
    _make_symlink(tmp_path / "alias", outside)

    with pytest.raises(ServerError, match="[Ll]ink"):
        asset_import.import_assets(source, tmp_path / "alias/server", RECIPE)

    assert not list(outside.iterdir())


def test_recipe_cannot_overwrite_asset_ownership_metadata(tmp_path):
    source = tmp_path / "owned"
    (source / ".alphagsm").mkdir(parents=True)
    (source / ".alphagsm/assets.json").write_text("operator manifest")
    recipe = {"include": (".alphagsm/*.json",), "required": (".alphagsm/assets.json",)}

    with pytest.raises(ServerError, match="metadata|reserved"):
        asset_import.import_assets(source, tmp_path / "server", recipe)


def test_existing_destination_case_collision_is_rejected(tmp_path):
    source = write_tree(tmp_path / "owned")
    destination = tmp_path / "server"
    (destination / "game/Halo3").mkdir(parents=True)

    with pytest.raises(ServerError, match="[Cc]ase|collision"):
        asset_import.import_assets(source, destination, RECIPE)

    assert [path.name for path in (destination / "game").iterdir()] == ["Halo3"]


def test_manifest_publication_failure_restores_owned_assets(tmp_path, monkeypatch):
    source = write_tree(tmp_path / "owned")
    destination = tmp_path / "server"
    asset_import.import_assets(source, destination, RECIPE)
    before = (destination / ".alphagsm/assets.json").read_bytes()
    (source / "halo3/halo3.dll").write_text("new engine")
    real_replace = os.replace

    def fail_manifest(src, dst):
        if Path(dst).as_posix().endswith(".alphagsm/assets.json"):
            raise OSError("manifest publication failed")
        return real_replace(src, dst)

    monkeypatch.setattr(asset_import.os, "replace", fail_manifest)
    with pytest.raises(ServerError, match="manifest publication failed"):
        asset_import.import_assets(source, destination, RECIPE)

    assert (destination / "game/halo3/halo3.dll").read_text() == "engine"
    assert (destination / ".alphagsm/assets.json").read_bytes() == before


def test_check_applies_case_normalization_to_recipe_required_paths(tmp_path):
    recipe = dict(RECIPE, case_insensitive=True, required=("Halo3/Halo3.DLL", "Halo3/Maps/Shared.MAP"))
    source = write_tree(tmp_path / "owned")
    asset_import.import_assets(source, tmp_path / "server", recipe)

    assert asset_import.check_assets(tmp_path / "server", recipe)["ready"]


def test_export_rejects_indirect_normalized_output_inside_source(tmp_path):
    source = write_tree(tmp_path / "owned")
    (tmp_path / "other").mkdir()

    with pytest.raises(ServerError, match="[Oo]utput|source"):
        asset_import.export_assets(source, tmp_path / "other/../owned/transfer.zip", RECIPE)


def test_case_insensitive_recipe_normalizes_declared_root(tmp_path):
    source = write_tree(tmp_path / "owned/game")
    recipe = dict(RECIPE, roots=("GAME",), case_insensitive=True)

    report = asset_import.import_assets(source.parent, tmp_path / "server", recipe)

    assert len(report["copied"]) == 2


def test_export_cannot_replace_case_normalized_source_asset(tmp_path):
    source = tmp_path / "owned"
    (source / "GAME/Halo3/Maps").mkdir(parents=True)
    engine = source / "GAME/Halo3/Halo3.DLL"
    engine.write_bytes(b"original engine")
    (source / "GAME/Halo3/Maps/Shared.MAP").write_bytes(b"original maps")
    recipe = dict(RECIPE, case_insensitive=True)

    with pytest.raises(ServerError, match="[Oo]utput|source"):
        asset_import.export_assets(source, engine, recipe)

    assert engine.read_bytes() == b"original engine"
    assert (source / "GAME/Halo3/Maps/Shared.MAP").read_bytes() == b"original maps"
