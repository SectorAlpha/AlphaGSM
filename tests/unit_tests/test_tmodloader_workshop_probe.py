"""Native Census output is framed by the server's optional console prompt."""

from tests.smoke_tests.tmodloader_workshop import npc_counts


def test_native_census_names_accept_prompt_and_console_ansi():
    output = '\x1b[?25h: Guide\r\nMerchant\n\x1b[33mNurse\x1b[0m\n'
    assert npc_counts(output) == {'Guide': 1, 'Merchant': 1, 'Nurse': 1}


def test_metadata_or_command_echo_is_not_native_npc_output():
    assert npc_counts('Enabled: Census\nTownProgress Guide Merchant Nurse\n') == {
        'Guide': 0, 'Merchant': 0, 'Nurse': 0}
