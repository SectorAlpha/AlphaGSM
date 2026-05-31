from scripts.generate_game_server_support_tracker import (
    parse_status_sections,
    render_support_tracker,
)


def test_parse_status_sections_includes_enabled_byo():
    text = """
## PASSED (1)
| Test | Type |
|------|------|
| acserver | SteamCMD |

## ENABLED (BYO) (2)
| Test | Type |
|------|------|
| cod2server | bring-your-own-assets |
| dstserver | bring-your-own-config |

## DISABLED (1)
| Test | Reason |
|------|--------|
| bfvserver | dead URL |

## SKIPPED (1)
| Test | Skip reason |
|------|-------------|
| stormworksserver | redirected |
"""
    rows = parse_status_sections(text)
    assert rows["PASSED"] == ["acserver"]
    assert rows["ENABLED (BYO)"] == ["cod2server", "dstserver"]
    assert rows["DISABLED"] == ["bfvserver"]
    assert rows["SKIPPED"] == ["stormworksserver"]


def test_parse_status_sections_includes_enabled_auth():
    text = """
## PASSED (1)
| Test | Type |
|------|------|
| acserver | SteamCMD |

## ENABLED (AUTH) (1)
| Test | Type |
|------|------|
| tiserver | eos credentials |
"""
    rows = parse_status_sections(text)
    assert rows["ENABLED (AUTH)"] == ["tiserver"]


def test_render_support_tracker_counts_enabled_byo_as_supported():
    rows = {
        "PASSED": ["acserver"],
        "ENABLED (AUTH)": ["tiserver"],
        "ENABLED (BYO)": ["cod2server"],
        "DISABLED": ["bfvserver"],
        "SKIPPED": ["stormworksserver"],
    }
    rendered = render_support_tracker(rows)
    assert "## Supported Now" in rendered
    assert "- [x] acserver" in rendered
    assert "- [x] tiserver" in rendered
    assert "- [x] cod2server" in rendered
    assert "- [ ] bfvserver" in rendered
    assert "- [ ] stormworksserver" in rendered
