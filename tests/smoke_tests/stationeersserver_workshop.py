"""Prove native loading and world construction for a public XML world mod."""

import argparse
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile

FIXTURE_ID = "3779655608"
FIXTURE_NAME = "Mars Abandoned Frontier"
WORLD = "AbandonedMars"


def assert_workshop_loaded(log_text, save_path):
    """Require native execution evidence and matching engine-created save data."""
    assert f"successfully loaded the '{FIXTURE_NAME}' mod" in log_text
    assert f"WorldSetting: {WORLD} StartCondition:" in log_text
    assert "Started new game. Saving..." in log_text
    with zipfile.ZipFile(save_path) as archive:
        for name in ("world_meta.xml", "world.xml"):
            assert archive.getinfo(name).file_size <= 64 * 1024 * 1024
        metadata = ET.fromstring(archive.read("world_meta.xml"))
        world = ET.fromstring(archive.read("world.xml"))
    assert metadata.tag == "WorldMetaData" and metadata.findtext("WorldName") == WORLD
    assert world.tag == "WorldData" and world.find("WorldSetting").get("Id") == WORLD
    things = world.find("AllThings")
    assert things is not None and any(
        (thing.findtext("PrefabName") or "").startswith("Structure") for thing in things
    ), "The engine did not save constructed world structures"


def main():
    """Inspect the fresh log and save from an owned smoke lifecycle."""
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("save", type=Path)
    arguments = parser.parse_args()
    assert_workshop_loaded(arguments.log.read_text(errors="replace"), arguments.save)


if __name__ == "__main__":
    main()
