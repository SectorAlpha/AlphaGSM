from server.module_catalog import load_default_module_catalog


def test_alias_catalog_points_to_expected_targets():
    catalog = load_default_module_catalog()

    assert catalog.aliases["tf2"] == "teamfortress2"
    assert catalog.aliases["tf2server"] == "teamfortress2"
    assert catalog.aliases["tf2c"] == "tf2cserver"
    assert catalog.aliases["tf2classifiedserver"] == "tf2cserver"
    assert catalog.aliases["cs2server"] == "counterstrike2"
    assert catalog.aliases["csgo"] == "counterstrikeglobaloffensive"
    assert catalog.aliases["csgoserver"] == "counterstrikeglobaloffensive"
    assert catalog.aliases["ctserver"] == "craftopiaserver"
    assert catalog.aliases["mcserver"] == "minecraft.vanilla"
    assert catalog.aliases["pmcserver"] == "minecraft.paper"
    assert catalog.aliases["terrariaserver"] == "terraria.vanilla"
    assert catalog.aliases["vpmcserver"] == "minecraft.velocity"
    assert catalog.aliases["wmcserver"] == "minecraft.waterfall"
    assert catalog.aliases["risingstorm2vietnam"] == "rs2server"
    assert catalog.namespace_defaults["minecraft"] == "minecraft.vanilla"
    assert catalog.namespace_defaults["terraria"] == "terraria.vanilla"
    assert catalog.namespace_defaults["arma3"] == "arma3.vanilla"


def test_catalog_alias_values_are_real_modules():
    catalog = load_default_module_catalog()
    canonical = set(catalog.canonical_modules)

    assert set(catalog.aliases.values()).issubset(canonical)
    assert set(catalog.namespace_defaults.values()).issubset(canonical)
