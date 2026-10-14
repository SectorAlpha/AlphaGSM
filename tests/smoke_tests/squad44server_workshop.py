"""Current Linux Squad 44 fixture identity derived from the staged native plugin."""

import argparse
import configparser
import json
from pathlib import Path
import re
import time

from server.modsupport.workshop import normalize_workshop_identifier

# Author patch notes explicitly add Linux support on 8 May 2025:
# https://steamcommunity.com/sharedfiles/filedetails/?id=2387944294
# Actual anonymous access and current engine compatibility remain CI assertions.
FIXTURE_ID = "2387944294"
FIXTURE_LAYER = "Ramelle_Offensive_01"


def select_workshop_layer(item_id, override=""):
    """Use the author's Ramelle layer or require an explicit override fixture layer."""
    layer = override or (FIXTURE_LAYER if normalize_workshop_identifier(item_id) == FIXTURE_ID else "")
    assert layer, "An override Workshop fixture requires an explicit native layer"
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_ -]{0,127}", layer), "Invalid native layer"
    return layer


def configure_workshop_layer(install_dir, layer):
    """Select one native layer in this stopped disposable install's rotation."""
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_ -]{0,127}", layer), "Invalid native layer"
    root = Path(install_dir)
    config = root / "PostScriptum/ServerConfig"
    rotation = config / "MapRotation.cfg"
    assert config.is_dir(), "Native server configuration is missing"
    assert all(not path.is_symlink() for path in (root, root / "PostScriptum", config, rotation))
    assert rotation.resolve().is_relative_to(root.resolve()), "Native rotation escaped test install"
    rotation.write_text(layer + "\n", encoding="utf-8")


def _layer_identity(value):
    return re.sub(r"[ _-]", "", value).casefold()


def assert_native_map_loaded(log_text, layer):
    """A mounted PAK or a registry listing cannot stand in for a constructed world."""
    expected = _layer_identity(layer)
    loaded = re.findall(r"LogLoad: Took [0-9.]+ seconds to LoadMap\(([^)\r\n]+)\)", log_text)
    worlds = re.findall(r"LogWorld: Bringing World ([^\s]+) up for play", log_text)
    def matching(path):
        name = path.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1].split(".", 1)[0]
        return path.startswith("/") and _layer_identity(name) == expected
    assert any(matching(path) for path in loaded), f"No completed native LoadMap for {layer}"
    assert any(matching(path) for path in worlds), f"No native world brought up for play for {layer}"


def assert_workshop_map_info(info, layer):
    """Require actual A2S layer identity, allowing only display-name separators."""
    assert info.get("protocol") == "a2s", "Workshop map requires real A2S metadata"
    assert _layer_identity(str(info.get("map", ""))) == _layer_identity(layer), (
        f"A2S did not report selected Workshop layer {layer}: {info.get('map')!r}")


def assert_native_plugin_loaded(runtime_text, native_text, plugin):
    """Retain early engine stdout emitted before the native log file opens."""
    assert re.fullmatch(r"[A-Za-z0-9_-]+", plugin), "Invalid native plugin name"
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", runtime_text + "\n" + native_text).replace("\r", "")
    prefix = r"^(?:\[[^\]\r\n]*\])*"
    identity = r"(?<![A-Za-z0-9_-])" + re.escape(plugin) + r"(?![A-Za-z0-9_-])"
    plugin_path = r"[/\\]" + re.escape(plugin) + r"[/\\]"
    assert re.search(prefix + r"LogPakFile:.*\bMounted Pak file\b.*" + plugin_path + r".*\.pak\b",
                     text, re.MULTILINE | re.IGNORECASE), "No native Workshop PAK mount"
    assert re.search(prefix + r"LogModdingRuntimeModule:.*\b(?:mounted|seriali[sz]ed)\b.*" + identity,
                     text, re.MULTILINE | re.IGNORECASE), "No native Workshop plugin registration"


def wait_for_native_map(log_dir, layer, timeout):
    """Wait for fresh native world completion; caller rotates logs before launch."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        text = "\n".join(path.read_text(errors="replace") for path in Path(log_dir).glob("*.log"))
        try:
            assert_native_map_loaded(text, layer)
            return text
        except AssertionError:
            time.sleep(2)
    raise AssertionError(f"Fresh engine log did not complete Workshop world {layer}")


def staged_plugin_name(install_dir, item_id, override=""):
    """Require one bounded native plugin with matching Workshop and SDK identity."""
    item_id = normalize_workshop_identifier(item_id)
    assert re.fullmatch(r"[0-9]+", item_id), "Workshop fixture ID must be numeric"
    root = Path(install_dir) / "PostScriptum/Plugins/Mods" / item_id
    assert root.is_dir() and not root.is_symlink(), "Workshop fixture was not staged"
    descriptors = []
    for index, path in enumerate(root.rglob("*")):
        assert index < 10000, "Workshop fixture exceeds file inspection limit"
        assert not path.is_symlink(), "Workshop fixture contains a symlink"
        if path.suffix == ".uplugin" and path.is_file():
            descriptors.append(path)
    if override:
        assert re.fullmatch(r"[A-Za-z0-9_-]+", override), "Invalid native plugin override"
        descriptors = [path for path in descriptors if path.stem == override]
    assert len(descriptors) == 1, "Expected exactly one matching native Workshop plugin"
    descriptor = descriptors[0]
    assert re.fullmatch(r"[A-Za-z0-9_-]+", descriptor.stem), "Invalid native plugin name"
    assert descriptor.stat().st_size <= 1024 * 1024, "Plugin descriptor exceeds 1 MiB"
    metadata = json.loads(descriptor.read_text(encoding="utf-8-sig"))
    assert metadata.get("FileVersion") == 3 and metadata.get("CanContainContent") is True
    identity_file = descriptor.with_suffix(".mi")
    assert not identity_file.is_symlink() and identity_file.is_file(), "Native mod identity is missing"
    assert identity_file.stat().st_size <= 1024 * 1024, "Native mod identity exceeds 1 MiB"
    identity = configparser.RawConfigParser()
    identity.read_string(identity_file.read_text(encoding="utf-8-sig"))
    assert identity.get("Modding.Core", "ID") == item_id, "Native Workshop identity mismatch"
    assert identity.get("Modding.Core", "Engine") == "4.27.2.SQ44", "Workshop fixture SDK is incompatible"
    return descriptor.stem


def main():
    """Print only the validated plugin name for the smoke runner."""
    parser = argparse.ArgumentParser()
    parser.add_argument("install_dir", type=Path)
    parser.add_argument("item_id")
    parser.add_argument("--plugin", default="")
    parser.add_argument("--layer", default="")
    parser.add_argument("--configure-layer", action="store_true")
    parser.add_argument("--wait-for-map", type=int)
    parser.add_argument("--info-json", type=Path)
    parser.add_argument("--runtime-log", type=Path)
    args = parser.parse_args()
    plugin = staged_plugin_name(args.install_dir, args.item_id, args.plugin)
    layer = select_workshop_layer(args.item_id, args.layer)
    if args.configure_layer:
        configure_workshop_layer(args.install_dir, layer)
    native_log = ""
    if args.wait_for_map is not None:
        native_log = wait_for_native_map(args.install_dir / "PostScriptum/Saved/Logs", layer, args.wait_for_map)
    if args.runtime_log is not None:
        if not native_log:
            native_log = "\n".join(path.read_text(errors="replace")
                                   for path in (args.install_dir / "PostScriptum/Saved/Logs").glob("*.log"))
        assert_native_plugin_loaded(args.runtime_log.read_text(errors="replace"), native_log, plugin)
    if args.info_json is not None:
        assert_workshop_map_info(json.loads(args.info_json.read_text()), layer)
    print(plugin)


if __name__ == "__main__":
    main()
