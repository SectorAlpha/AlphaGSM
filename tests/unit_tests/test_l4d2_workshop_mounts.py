"""The load verifier requires fresh engine mount output, not downloaded files."""

import importlib.util
from pathlib import Path

import pytest


def verifier():
    path = Path(__file__).parents[1] / "smoke_tests/l4d2_workshop.py"
    spec = importlib.util.spec_from_file_location("l4d2_workshop_mounts", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mount_output_requires_every_requested_vpk():
    check = verifier()
    text = ('AlphaGSM-Workshop-Mounts-BEGIN\n'
            'GAME /srv/server/left4dead2/addons/workshop/10.vpk (vpk)\n'
            'GAME /srv/server/left4dead2/addons/workshop/11.vpk (vpk)\n'
            'AlphaGSM-Workshop-Mounts-END\n')
    check.assert_workshop_mounts(text, ["10", "11"])
    with pytest.raises(AssertionError, match="12"):
        check.assert_workshop_mounts(text, ["10", "12"])


@pytest.mark.parametrize("text", [
    'Downloaded /srv/server/left4dead2/addons/workshop/10.vpk',
    'AlphaGSM-Workshop-Mounts-BEGIN\nUnknown command "path"\nAlphaGSM-Workshop-Mounts-END',
    'AlphaGSM-Workshop-Mounts-BEGIN\nCan\'t load malformed vpk "/srv/server/left4dead2/addons/workshop/10.vpk"\nAlphaGSM-Workshop-Mounts-END',
    'AlphaGSM-Workshop-Mounts-BEGIN\nGAME /srv/server/left4dead2/addons/workshop/10.vpk',
    'AlphaGSM-Workshop-Mounts-BEGIN\nDownloaded /srv/server/left4dead2/addons/workshop/10.vpk\nAlphaGSM-Workshop-Mounts-END',
])
def test_downloads_stale_or_failed_mounts_are_not_load_proof(text):
    with pytest.raises(AssertionError):
        verifier().assert_workshop_mounts(text, ["10"])


def test_nonce_probe_ignores_previous_successful_mount_output():
    check = verifier()
    old = ('AlphaGSM-Workshop-Mounts-BEGIN\n'
           'GAME /srv/left4dead2/addons/workshop/10.vpk (vpk)\n'
           'AlphaGSM-Workshop-Mounts-END\n')
    with pytest.raises(AssertionError):
        check.assert_workshop_mounts(old, ['10'], begin_marker='BEGIN-fresh', end_marker='END-fresh')
    check.assert_workshop_mounts(old + 'BEGIN-fresh\n'
                                'GAME /srv/left4dead2/addons/workshop/10.vpk (vpk)\nEND-fresh\n',
                                ['10'], begin_marker='BEGIN-fresh', end_marker='END-fresh')


def test_native_addon_load_order_accepts_exact_engine_paths():
    verifier().assert_workshop_mounts('AlphaGSM-Workshop-Mounts-BEGIN\n'
                                     '/srv/server/left4dead2/addons/workshop/10.vpk\n'
                                     'AlphaGSM-Workshop-Mounts-END\n', ['10'])
