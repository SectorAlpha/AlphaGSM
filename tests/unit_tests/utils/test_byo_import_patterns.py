"""Owned data patterns must validate before any content is published."""
import pytest

from server import ServerError
from utils.asset_import import import_assets


def test_required_pattern_selects_owned_data_from_wrapped_game_directory(tmp_path):
    source = tmp_path / "owned"
    content = source / "Game/main"
    content.mkdir(parents=True)
    (content / "localized_english.iwd").write_bytes(b"owned content")
    (content / "savegame.dat").write_bytes(b"unrelated")
    target = tmp_path / "server"
    result = import_assets(source,target,{"roots":[""],"required":["main/localized_*.iwd"],
                                         "include":["main/*.iwd"],"target":""})
    assert result["copied"] == ["main/localized_english.iwd"]
    assert not (target / "main/savegame.dat").exists()


def test_required_pattern_must_match_nonempty_included_file(tmp_path):
    source=tmp_path/'owned'
    source.mkdir()
    (source/'empty.pk3').write_bytes(b'')
    target=tmp_path/'server'
    with pytest.raises(ServerError,match='Missing or empty'):
        import_assets(source,target,{"required":["*.pk3"],"include":["*.pk3"]})
    assert not target.exists()
    (source/'full.pk3').write_bytes(b'content')
    with pytest.raises(ServerError,match='include'):
        import_assets(source,target,{"required":["*.pk3"],"include":["*.cfg"]})
    assert not target.exists()


def test_explicit_required_alternatives_accept_config_only_base_assets(tmp_path):
    source = tmp_path / 'owned'
    (source / 'main').mkdir(parents=True)
    (source / 'main/default_mp.cfg').write_bytes(b'owned default')
    target = tmp_path / 'server'
    result = import_assets(source, target, {
        'required_any': [['main/pak0.pk3', 'main/default_mp.cfg']],
        'include': ['main/*.pk3', 'main/default_mp.cfg'],
    })
    assert result['copied'] == ['main/default_mp.cfg']
