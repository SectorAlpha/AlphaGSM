import io
import tarfile

import pytest

from server.modsupport.downloads import (
    download_to_cache,
    extract_tarball_safe,
    install_staged_tree,
)
from server.modsupport.errors import ModSupportError
from server.modsupport.ownership import build_owned_manifest


def test_download_to_cache_rejects_untrusted_host(tmp_path):
    with pytest.raises(ModSupportError, match="evil.invalid"):
        download_to_cache(
            "https://evil.invalid/mod.tar.gz",
            allowed_hosts={"trusted.invalid"},
            target_path=tmp_path / "mod.tar.gz",
        )


def test_extract_tarball_safe_rejects_path_traversal(tmp_path):
    tar_path = tmp_path / "mod.tar"
    extract_root = tmp_path / "extract"

    with tarfile.open(tar_path, "w") as archive:
        member = tarfile.TarInfo("../escape.txt")
        payload = b"nope"
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))

    with pytest.raises(ModSupportError, match="escape.txt"):
        extract_tarball_safe(tar_path, extract_root)


def test_install_staged_tree_rejects_paths_outside_allowed_destinations(tmp_path):
    staged_root = tmp_path / "stage"
    server_root = tmp_path / "server"
    (staged_root / "cfg").mkdir(parents=True)
    (staged_root / "cfg" / "server.cfg").write_text("hostname test", encoding="utf-8")

    with pytest.raises(ModSupportError, match="cfg/server.cfg"):
        install_staged_tree(
            staged_root=staged_root,
            server_root=server_root,
            allowed_destinations={"tf/addons", "tf/custom"},
        )


def test_build_owned_manifest_returns_sorted_relative_paths(tmp_path):
    server_root = tmp_path / "server"
    first = server_root / "tf" / "addons" / "zeta.txt"
    second = server_root / "tf" / "addons" / "alpha.txt"
    first.parent.mkdir(parents=True, exist_ok=True)
    first.write_text("z", encoding="utf-8")
    second.write_text("a", encoding="utf-8")

    manifest = build_owned_manifest(server_root, [first, second])

    assert manifest == ["tf/addons/alpha.txt", "tf/addons/zeta.txt"]
