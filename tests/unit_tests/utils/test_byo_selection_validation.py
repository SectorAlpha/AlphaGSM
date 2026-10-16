"""Imported/exported file selections satisfy the same per-game checks."""
from types import SimpleNamespace
import pytest

from server import ServerError
from utils.asset_import import import_assets, export_assets
from utils.byo_files import inspect_files


def test_cod_wrong_map_cannot_be_imported_or_exported(tmp_path):
    from gamemodules import codserver
    source=tmp_path/'owned'
    (source/'main').mkdir(parents=True)
    (source/'main/pak0.pk3').write_bytes(b'not a valid map archive')
    recipe=codserver.get_asset_requirements(SimpleNamespace(name='test',data={'startmap':'mp_test'}))
    with pytest.raises(ServerError,match='required'):
        import_assets(source,tmp_path/'server',recipe)
    with pytest.raises(ServerError,match='required'):
        export_assets(source,tmp_path/'export.zip',recipe)
    assert not (tmp_path/'server').exists()
    assert not (tmp_path/'export.zip').exists()


def test_cod2_incomplete_localized_data_is_rejected_before_publication(tmp_path):
    from gamemodules import cod2server
    source=tmp_path/'owned'
    (source/'main').mkdir(parents=True)
    (source/'main/unrelated.iwd').write_bytes(b'content')
    recipe=cod2server.get_asset_requirements(SimpleNamespace(name='test',data={}))
    with pytest.raises(ServerError,match='required'):
        import_assets(source,tmp_path/'server',recipe)
    assert not (tmp_path/'server').exists()


def test_cod4_preserves_exact_native_case_and_satisfies_lifecycle_validator(tmp_path):
    from gamemodules import cod4server
    source=tmp_path/'owned'
    (source/'main').mkdir(parents=True)
    (source/'zone/english').mkdir(parents=True)
    (source/'fileSysCheck.cfg').write_bytes(b'owned config')
    (source/'main/localized_english.iwd').write_bytes(b'owned game data')
    (source/'zone/english/mp.ff').write_bytes(b'fastfile')
    target=tmp_path/'server'
    recipe=cod4server.get_asset_requirements(SimpleNamespace(name='test',data={}))
    import_assets(source,target,recipe)
    assert (target/'fileSysCheck.cfg').is_file()
    cod4server._assert_required_base_assets(str(target))
    assert inspect_files(target,recipe)['ready']


def test_cod4_requires_localization_in_addition_to_general_iwd(tmp_path):
    from gamemodules import cod4server
    (tmp_path/'main').mkdir()
    (tmp_path/'zone').mkdir()
    (tmp_path/'main/unrelated.iwd').write_bytes(b'content')
    (tmp_path/'zone/test.ff').write_bytes(b'zone')
    (tmp_path/'fileSysCheck.cfg').write_bytes(b'cfg')
    recipe=cod4server.get_asset_requirements(SimpleNamespace(name='test',data={}))
    assert not inspect_files(tmp_path,recipe)['ready']
