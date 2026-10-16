"""Resolve fake Steam libraries using public, local metadata only."""

import importlib
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from server import ServerError


def resolver():
    spec = importlib.util.find_spec("utils.steam_library")
    assert spec is not None, "read-only Steam library resolution is missing"
    return importlib.import_module("utils.steam_library").find_installed_app


def quoted(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def install(root, app_id=123, name="Example Game"):
    apps = root / "steamapps"
    game = apps / "common" / name
    game.mkdir(parents=True)
    manifest(apps, f'"AppState" {{ "appid" "{app_id}" "installdir" {quoted(name)} }}', app_id)
    return game


def manifest(apps, content, app_id=123):
    apps.mkdir(parents=True, exist_ok=True)
    path = apps / f"appmanifest_{app_id}.acf"
    path.write_text(content, encoding="utf-8")
    return path


def libraries(root, entries, *, config=False, legacy=False):
    (root / "steamapps").mkdir(parents=True, exist_ok=True)
    location = root / ("config" if config else "steamapps") / "libraryfolders.vdf"
    location.parent.mkdir(parents=True, exist_ok=True)
    values = []
    for index, path in enumerate(entries):
        value = quoted(path)
        if not legacy:
            value = '{ "path" ' + value + ' "apps" { "123" "100" } }'
        values.append(f'"{index}" {value}')
    location.write_text('"libraryfolders" { ' + ' '.join(values) + ' }', encoding="utf-8")
    return location


def symlink_or_skip(link, target, *, directory=False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError):
        pytest.skip("host does not permit symbolic links")


def test_resolves_primary_library_without_inspecting_game_files(tmp_path):
    game = install(tmp_path)
    (game / "unrelated.bin").write_bytes(b"opaque data")
    assert resolver()(tmp_path, 123) == game.resolve()


def test_explicit_steamapps_restricts_resolution_to_that_library(tmp_path):
    client = tmp_path / "client"
    other = tmp_path / "other"
    expected = install(client)
    install(other)
    libraries(client, [other])
    assert resolver()(client / "steamapps", "123") == expected.resolve()
    with pytest.raises(ServerError, match="multiple|ambiguous"):
        resolver()(client, 123)


@pytest.mark.parametrize("config,legacy", [(False, False), (True, False), (False, True), (True, True)])
def test_finds_listed_modern_and_legacy_libraries(tmp_path, config, legacy):
    client = tmp_path / "client"
    expected = install(tmp_path / "Steam Library With Spaces")
    libraries(client, [expected.parents[2]], config=config, legacy=legacy)
    assert resolver()(client, 123) == expected.resolve()


def test_combines_both_known_library_lists_and_skips_unavailable_roots(tmp_path):
    client = tmp_path / "client"
    expected = install(tmp_path / "secondary")
    libraries(client, [tmp_path / "missing"])
    libraries(client, [expected.parents[2]], config=True)
    assert resolver()(client, 123) == expected.resolve()


def test_deduplicates_canonical_libraries_and_allows_client_root_links(tmp_path):
    client = tmp_path / "client"
    expected = install(client)
    link = tmp_path / "steam-link"
    symlink_or_skip(link, client, directory=True)
    libraries(client, [client, link, client / "../client"])
    assert resolver()(link, 123) == expected.resolve()


def test_reads_only_known_public_metadata_without_recursive_scan(tmp_path, monkeypatch):
    game = install(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config/config.vdf").write_text("private-account-cache")
    (tmp_path / "config/loginusers.vdf").write_text("private-users")
    (tmp_path / "unrelated").mkdir()
    install(tmp_path / "unrelated")
    module = importlib.import_module("utils.steam_library") if importlib.util.find_spec("utils.steam_library") else None
    assert module is not None, "read-only Steam library resolution is missing"
    original = module.os.open
    opened = []
    def tracked(path, flags, *args, **kwargs):
        opened.append(Path(path))
        assert not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        return original(path, flags, *args, **kwargs)
    monkeypatch.setattr(module.os, "open", tracked)
    assert module.find_installed_app(tmp_path, 123) == game.resolve()
    assert opened == [tmp_path / "steamapps/appmanifest_123.acf"]


@pytest.mark.parametrize("app_id", [0, -1, 4294967296, True, None, 1.5, "", "../123", "123/", " 123", "+123", "1e2", "١٢٣", "9" * 100])
def test_rejects_nondecimal_or_out_of_range_app_ids_before_reading(tmp_path, app_id):
    with pytest.raises(ServerError, match="app ID"):
        resolver()(tmp_path, app_id)


@pytest.mark.parametrize("app_id", [1, 4294967295, "123", "000123"])
def test_accepts_valid_decimal_app_ids(tmp_path, app_id):
    expected = install(tmp_path, int(app_id))
    assert resolver()(tmp_path, app_id) == expected.resolve()


def test_reports_missing_install_without_disclosing_unrelated_app(tmp_path):
    install(tmp_path, 456, "Secret Different Game")
    with pytest.raises(ServerError, match="not installed|No installed") as error:
        resolver()(tmp_path, 123)
    assert "Secret Different Game" not in str(error.value)


def test_reports_missing_or_invalid_explicit_roots(tmp_path):
    with pytest.raises(ServerError, match="Steam directory"):
        resolver()(tmp_path / "missing", 123)
    path = tmp_path / "file"
    path.touch()
    with pytest.raises(ServerError, match="Steam directory"):
        resolver()(path, 123)


@pytest.mark.parametrize("contents", [
    '"AppState" { "appid" "456" "installdir" "Example Game" }',
    '"AppState" { "appid" "0123" "installdir" "Example Game" }',
    '"AppState" { "nested" { "appid" "123" } "installdir" "Example Game" }',
    '"OtherState" { "appid" "123" "installdir" "Example Game" }',
    '"AppState" "123"',
    '"AppState" { "appid" { "value" "123" } "installdir" "Example Game" }',
    '"AppState" { "appid" "123" "nested" { "installdir" "Example Game" } }',
])
def test_manifest_fields_must_belong_to_matching_appstate(tmp_path, contents):
    install(tmp_path)
    manifest(tmp_path / "steamapps", contents)
    with pytest.raises(ServerError, match="manifest"):
        resolver()(tmp_path, 123)


@pytest.mark.parametrize("name", ["", ".", "..", "../outside", "a/b", "a\\b", "/absolute", "C:drive", "name.", "name ", "CON", "nul.txt", "bad?name", "bad\nname", "bad\x7fname"])
def test_rejects_unsafe_or_nonportable_installdir(tmp_path, name):
    manifest(tmp_path / "steamapps", f'"AppState" {{ "appid" "123" "installdir" {quoted(name)} }}')
    with pytest.raises(ServerError, match="installdir"):
        resolver()(tmp_path, 123)


@pytest.mark.parametrize("name", ["COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³",
                                 "COM¹.txt", "COM².txt", "COM³.txt", "LPT¹.txt", "LPT².txt", "LPT³.txt"])
def test_rejects_windows_reserved_superscript_installdir(tmp_path, name):
    manifest(tmp_path / "steamapps", f'"AppState" {{ "appid" "123" "installdir" {quoted(name)} }}')
    with pytest.raises(ServerError, match="installdir"):
        resolver()(tmp_path, 123)


def test_rejects_install_symlink_escaping_common_directory(tmp_path):
    install(tmp_path)
    target = tmp_path / "outside"
    target.mkdir()
    game = tmp_path / "steamapps/common/Example Game"
    game.rmdir()
    symlink_or_skip(game, target, directory=True)
    with pytest.raises(ServerError, match="escapes"):
        resolver()(tmp_path, 123)


def test_missing_game_directory_is_not_an_installed_app(tmp_path):
    game = install(tmp_path)
    game.rmdir()
    with pytest.raises(ServerError, match="not installed|No installed"):
        resolver()(tmp_path, 123)


@pytest.mark.parametrize("body", [
    '"AppState" { "appid" "123" "installdir" "Example Game"',
    '"AppState" { "appid" "123" "installdir" }',
    '"AppState" { "appid" "123" "installdir" "Example Game" } }',
    '"AppState" { "appid" "123" "appid" "123" "installdir" "Example Game" }',
    '"AppState" { "appid" "123" "AppID" "123" "installdir" "Example Game" }',
    '"AppState" { "appid" "123" "installdir" "Example Game" } "AppState" {}',
    'AppState { "appid" "123" "installdir" "Example Game" }',
    '#include "private-file"',
    '"AppState" { "appid" "123" "installdir" "Example Game" } [windows]',
    '"AppState" { "appid" "123" "installdir" "bad\\qescape" }',
    '"AppState" { "appid" "123" "installdir" "unterminated }',
    '"AppState" { "appid" "123" "installdir" "Example Game" }\x00',
])
def test_rejects_malformed_or_unsupported_keyvalues_without_echoing_content(tmp_path, body):
    install(tmp_path)
    manifest(tmp_path / "steamapps", body + '\n// secret-marker')
    with pytest.raises(ServerError, match="metadata") as error:
        resolver()(tmp_path, 123)
    assert "secret-marker" not in str(error.value)


def test_keyvalues_supports_comments_nested_objects_and_escaped_quotes(tmp_path):
    game = install(tmp_path)
    manifest(tmp_path / "steamapps", r'''// public manifest
"AppState" {
    "appid" "123" // explanatory comment
    "installdir" "Example Game"
    "name" "A \"quoted\" name with \\ slash // text"
    "MountedDepots" { "1" "2" }
}
''')
    assert resolver()(tmp_path, 123) == game.resolve()


def test_keyvalues_library_paths_support_escaped_windows_separators_or_quotes(tmp_path):
    client = tmp_path / "client"
    name = "Steam Library"
    if os.name != "nt":
        name += ' "quoted" \\ path'
    expected = install(tmp_path / name)
    libraries(client, [expected.parents[2]])
    assert resolver()(client, 123) == expected.resolve()


@pytest.mark.parametrize("depth", [17, 100])
def test_rejects_excessive_keyvalues_nesting(tmp_path, depth):
    game = install(tmp_path)
    nested = '"child" { ' * depth + '"x" "y"' + ' }' * depth
    manifest(tmp_path / "steamapps", f'"AppState" {{ "appid" "123" "installdir" {quoted(game.name)} {nested} }}')
    with pytest.raises(ServerError, match="metadata"):
        resolver()(tmp_path, 123)


def test_accepts_sixteen_levels_of_keyvalues_nesting(tmp_path):
    game = install(tmp_path)
    nested = '"child" { ' * 15 + '"x" "y"' + ' }' * 15
    manifest(tmp_path / "steamapps", f'"AppState" {{ "appid" "123" "installdir" {quoted(game.name)} {nested} }}')
    assert resolver()(tmp_path, 123) == game.resolve()


@pytest.mark.parametrize("kind", ["manifest", "libraries"])
def test_rejects_oversized_metadata(tmp_path, kind):
    install(tmp_path)
    path = tmp_path / "steamapps" / ("appmanifest_123.acf" if kind == "manifest" else "libraryfolders.vdf")
    path.write_bytes(b" " * (1024 * 1024 + 1))
    with pytest.raises(ServerError, match="1 MiB|too large|exceeds"):
        resolver()(tmp_path, 123)


@pytest.mark.parametrize("kind", ["manifest", "libraries"])
def test_rejects_metadata_symlinks(tmp_path, kind):
    install(tmp_path)
    path = tmp_path / "steamapps" / ("appmanifest_123.acf" if kind == "manifest" else "libraryfolders.vdf")
    path.unlink(missing_ok=True)
    target = tmp_path / "public-copy"
    target.write_text('"AppState" { "appid" "123" "installdir" "Example Game" }')
    symlink_or_skip(path, target)
    with pytest.raises(ServerError, match="metadata"):
        resolver()(tmp_path, 123)


@pytest.mark.parametrize("kind", ["manifest", "libraries"])
def test_rejects_nonregular_metadata(tmp_path, kind):
    install(tmp_path)
    path = tmp_path / "steamapps" / ("appmanifest_123.acf" if kind == "manifest" else "libraryfolders.vdf")
    path.unlink(missing_ok=True)
    path.mkdir()
    with pytest.raises(ServerError, match="metadata"):
        resolver()(tmp_path, 123)


def test_rejects_fifo_metadata_without_opening_or_blocking(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("host does not support FIFOs")
    install(tmp_path)
    path = tmp_path / "steamapps/appmanifest_123.acf"
    path.unlink()
    os.mkfifo(path)
    with pytest.raises(ServerError, match="metadata"):
        resolver()(tmp_path, 123)


def test_rejects_metadata_reparse_points_on_all_platforms(tmp_path, monkeypatch):
    install(tmp_path)
    original = Path.lstat
    def reparse(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path.name == "appmanifest_123.acf":
            return SimpleNamespace(st_mode=stat.S_IFREG | 0o644,
                                   st_file_attributes=getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        return result
    monkeypatch.setattr(Path, "lstat", reparse)
    with pytest.raises(ServerError, match="metadata"):
        resolver()(tmp_path, 123)


def test_rejects_invalid_utf8_metadata(tmp_path):
    install(tmp_path)
    (tmp_path / "steamapps/appmanifest_123.acf").write_bytes(b"\xff secret-marker")
    with pytest.raises(ServerError, match="metadata") as error:
        resolver()(tmp_path, 123)
    assert "secret-marker" not in str(error.value)


def test_distinct_matching_manifests_are_ambiguous_even_when_games_resolve_together(tmp_path):
    client = tmp_path / "client"
    other = tmp_path / "other"
    install(client)
    other_apps = other / "steamapps"
    other_apps.mkdir(parents=True)
    symlink_or_skip(other_apps / "common", client / "steamapps/common", directory=True)
    manifest(other_apps, '"AppState" { "appid" "123" "installdir" "Example Game" }')
    libraries(client, [other])
    with pytest.raises(ServerError, match="multiple|ambiguous"):
        resolver()(client, 123)


@pytest.mark.parametrize("contents", [
    '"libraryfolders" "invalid"',
    '"other" { "0" "ignored" }',
    '"libraryfolders" { "0" { "apps" { "123" "1" } } }',
    '"libraryfolders" { "0" { "path" { "nested" "invalid" } } }',
    '"libraryfolders" { "0" "relative/path" }',
    '"libraryfolders" { "0" "" }',
    '"libraryfolders" { "0" "/first" "0" "/second" }',
])
def test_invalid_library_metadata_is_not_silently_ignored(tmp_path, contents):
    install(tmp_path)
    (tmp_path / "steamapps/libraryfolders.vdf").write_text(contents)
    with pytest.raises(ServerError, match="metadata"):
        resolver()(tmp_path, 123)


def test_metadata_at_size_limit_with_utf8_bom_is_supported(tmp_path):
    game = install(tmp_path)
    path = tmp_path / "steamapps/appmanifest_123.acf"
    original = b"\xef\xbb\xbf" + path.read_bytes()
    path.write_bytes(original + b" " * (1024 * 1024 - len(original)))
    assert resolver()(tmp_path, 123) == game.resolve()


def test_oversized_metadata_is_rejected_before_open(tmp_path, monkeypatch):
    install(tmp_path)
    path = tmp_path / "steamapps/appmanifest_123.acf"
    path.write_bytes(b" " * (1024 * 1024 + 1))
    module = importlib.import_module("utils.steam_library")
    monkeypatch.setattr(module.os, "open", lambda *_args, **_kwargs: pytest.fail("oversized file was opened"))
    with pytest.raises(ServerError, match="exceeds"):
        resolver()(tmp_path, 123)


def test_metadata_read_remains_bounded_if_file_grows_after_stat(tmp_path, monkeypatch):
    install(tmp_path)
    module = importlib.import_module("utils.steam_library")
    original = module.os.fdopen
    requests = []
    class GrowingReader:
        def __init__(self, stream):
            self.stream = stream
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.stream.close()
        def fileno(self):
            return self.stream.fileno()
        def read(self, size=-1):
            requests.append(size)
            assert 0 < size <= 1024 * 1024 + 1
            with (tmp_path / "steamapps/appmanifest_123.acf").open("ab") as writer:
                writer.write(b" " * (1024 * 1024 + 10))
            return self.stream.read(size)
    monkeypatch.setattr(module.os, "fdopen", lambda *args: GrowingReader(original(*args)))
    with pytest.raises(ServerError, match="exceeds"):
        resolver()(tmp_path, 123)
    assert requests == [1024 * 1024 + 1]


def test_replaced_metadata_is_rejected_before_reading(tmp_path, monkeypatch):
    install(tmp_path)
    module = importlib.import_module("utils.steam_library")
    replacement = tmp_path / "replacement"
    replacement.write_text('"AppState" { "appid" "123" "installdir" "Example Game" }')
    original = module.os.open
    def replaced(path, *args, **kwargs):
        if Path(path).name == "appmanifest_123.acf":
            return original(replacement, *args, **kwargs)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(module.os, "open", replaced)
    with pytest.raises(ServerError, match="changed"):
        resolver()(tmp_path, 123)


def test_metadata_os_errors_do_not_expose_raw_details(tmp_path, monkeypatch):
    install(tmp_path)
    module = importlib.import_module("utils.steam_library")
    def fail(*_args, **_kwargs):
        raise PermissionError("private-marker")
    monkeypatch.setattr(module.os, "open", fail)
    with pytest.raises(ServerError, match="metadata") as error:
        resolver()(tmp_path, 123)
    assert "private-marker" not in str(error.value)
