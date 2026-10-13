"""DST Workshop configuration preserves operator Lua and shard ownership."""

from types import SimpleNamespace

import pytest

from server import ServerError
from server.modsupport.errors import ModSupportError
from server.modsupport.native_workshop import write_managed_text
from gamemodules.dstserver import workshop as dst


@pytest.fixture
def instance(tmp_path):
    return SimpleNamespace(name='dst', data={'dir': str(tmp_path), 'confdir': 'DoNotStarveTogether',
                           'cluster': 'cluster', 'shard': 'Master', 'mods': {}})


def test_dst_native_configuration_enables_items_and_keeps_operator_lua(instance):
    path = 'DoNotStarveTogether/cluster/Master/modoverrides.lua'
    original = 'return { ["workshop-99"] = { enabled = true, configuration_options = { size = 3 } } }\n'
    write_managed_text(instance, path, original)
    write_managed_text(instance, 'mods/dedicated_server_mods_setup.lua', 'ServerModSetup("99")\n')
    files = dst.apply_workshop_configuration(instance, ['10', '20'])
    assert path in files
    from pathlib import Path
    root = Path(instance.data['dir'])
    setup = (root / 'mods/dedicated_server_mods_setup.lua').read_text()
    assert 'ServerModSetup("99")' in setup
    assert 'ServerModSetup("10")' in setup and 'ServerModSetup("20")' in setup
    overrides = (root / path).read_text()
    assert original.strip() in overrides
    assert 'workshop-10' in overrides and 'enabled = true' in overrides
    dst.apply_workshop_configuration(instance, [])
    assert (root / path).read_text() == original
    assert (root / 'mods/dedicated_server_mods_setup.lua').read_text() == 'ServerModSetup("99")\n'


def test_removed_mod_does_not_reappear_after_refresh(instance):
    from pathlib import Path
    dst.apply_workshop_configuration(instance, ['10', '20'])
    dst.apply_workshop_configuration(instance, ['20'])
    setup = (Path(instance.data['dir']) / 'mods/dedicated_server_mods_setup.lua').read_text()
    assert 'ServerModSetup("10")' not in setup
    assert setup.count('ServerModSetup("20")') == 1


def test_shard_change_restores_previous_shard(instance):
    from pathlib import Path
    old = 'DoNotStarveTogether/cluster/Master/modoverrides.lua'
    original = 'return { }\n'
    write_managed_text(instance, old, original)
    dst.apply_workshop_configuration(instance, ['10'])
    instance.data['shard'] = 'Caves'
    dst.apply_workshop_configuration(instance, ['10'])
    root = Path(instance.data['dir'])
    assert (root / old).read_text() == original
    assert 'workshop-10' in (root / 'DoNotStarveTogether/cluster/Caves/modoverrides.lua').read_text()


def test_operator_edit_blocks_reapply_and_cleanup(instance):
    path = 'DoNotStarveTogether/cluster/Master/modoverrides.lua'
    dst.apply_workshop_configuration(instance, ['10'])
    write_managed_text(instance, path, '-- manually changed\nreturn {}\n')
    with pytest.raises(ServerError, match='changed'):
        dst.apply_workshop_configuration(instance, [])


def test_all_config_paths_preflight_before_write(instance):
    from pathlib import Path
    root = Path(instance.data['dir'])
    outside = root.parent / f'{root.name}-external'
    outside.mkdir()
    (root / 'DoNotStarveTogether').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ServerError, match='symlink'):
        dst.apply_workshop_configuration(instance, ['10'])
    assert not (root / 'mods').exists()


@pytest.mark.parametrize('key', ['confdir', 'cluster', 'shard'])
def test_instance_names_cannot_escape(instance, key):
    instance.data[key] = '../escape'
    with pytest.raises(ServerError):
        dst.apply_workshop_configuration(instance, ['10'])


@pytest.mark.parametrize('failure', [OSError, ServerError])
def test_second_config_failure_restores_first_and_keeps_ownership(instance, monkeypatch, failure):
    from copy import deepcopy
    from pathlib import Path
    dst.apply_workshop_configuration(instance, ['10'])
    prior = deepcopy(instance.data['mods']['dst_workshop_files'])
    original_writer = dst.write_managed_text

    def fail_overrides(server, relative, text):
        if relative.endswith('modoverrides.lua'):
            raise failure('publication failed')
        return original_writer(server, relative, text)

    monkeypatch.setattr(dst, 'write_managed_text', fail_overrides)
    with pytest.raises(failure, match='publication failed'):
        dst.apply_workshop_configuration(instance, ['20'])
    assert instance.data['mods']['dst_workshop_files'] == prior
    for relative, record in prior.items():
        assert (Path(instance.data['dir']) / relative).read_text() == record['managed']


def test_invalid_item_cannot_change_native_files(instance):
    from pathlib import Path
    with pytest.raises(ModSupportError):
        dst.apply_workshop_configuration(instance, ['10', '20\"); os.execute("bad")'])
    assert not list(Path(instance.data['dir']).iterdir())


@pytest.mark.parametrize('character', ['x', 'é'])
def test_generated_config_limit_rejects_before_either_file_changes(instance, character):
    from pathlib import Path
    path = 'DoNotStarveTogether/cluster/Master/modoverrides.lua'
    original = '--' + character * ((dst.MAX_CONFIG_BYTES - 32) // len(character.encode('utf-8'))) + '\nreturn {}\n'
    write_managed_text(instance, path, original)
    with pytest.raises(ServerError, match='generated.*size limit'):
        dst.apply_workshop_configuration(instance, ['10'])
    root = Path(instance.data['dir'])
    assert (root / path).read_text() == original
    assert not (root / 'mods/dedicated_server_mods_setup.lua').exists()
    assert not instance.data['mods'].get('dst_workshop_files')
