import server.gamemodules as gamemodules_doc


def test_gamemodules_documentation_module_has_expected_sections():
    assert gamemodules_doc.__doc__ is not None
    assert "Commands:" in gamemodules_doc.__doc__
    assert "Setup:" in gamemodules_doc.__doc__
    assert "Backup:" in gamemodules_doc.__doc__
