# Wave 1 Canonical Set Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Roll the canonical `set` schema/discovery/native-config flow across the remaining 12 game modules that already expose `sync_server_config(...)`, including safely mappable upstream-native keys, per-module unit coverage, and matching docs/templates.

**Architecture:** Keep the shared `server.settable_keys` and `Server.doset(...)` contract unchanged unless a new cross-module rule is discovered. Implement the wave in config-style batches, letting each module own its own `setting_schema`, `checkvalue(...)`, `sync_server_config(...)`, and `list_setting_values(...)` behavior while using common canonical naming conventions (`map`, `servername`, `serverpassword`, `adminpassword`, `rconpassword`, `maxplayers`, `port`, `queryport`).

**Tech Stack:** Python, `pytest`, existing AlphaGSM module contract in `src/server/gamemodules.py`, the shared resolver in `src/server/settable_keys.py`, the `Server.doset(...)` discovery/write flow in `src/server/server.py`, plus format-specific helpers already used in JSON/properties/INI/XML/text modules.

---

## File Map

- Modify: `src/gamemodules/armarserver.py`
  Add schema-backed canonical keys for the Reforger JSON config, including `adminpassword` and `bindaddress`.
- Modify: `src/gamemodules/rimworldtogetherserver.py`
  Add schema-backed discovery for the verified RimWorld Together native config surface.
- Modify: `tests/unit_tests/gamemodules/test_armarserver_cov.py`
  Cover Reforger schema metadata, config sync, and canonical key validation.
- Modify: `tests/unit_tests/gamemodules/test_rimworldtogetherserver_cov.py`
  Cover RimWorld Together schema metadata and the verified native-config surface.
- Modify: `docs/servers/armarserver.md`
  Document canonical `set` usage for Reforger JSON-backed settings.
- Modify: `docs/server-templates/armarserver/server.json`
  Reflect the newly managed native JSON keys.
- Modify: `docs/servers/rimworldtogetherserver.md`
  Document the verified canonical `set` surface for RimWorld Together.
- Modify: `docs/server-templates/rimworldtogetherserver/ServerConfig.json`
  Reflect the verified schema-backed native config keys.
- Modify: `docs/server-templates/rimworldtogetherserver/ServerSettings.json`
  Keep the mirrored runtime example aligned where the module writes both files.

- Modify: `src/gamemodules/scpslserver.py`
  Add schema-backed canonical keys for SCP:SL gameplay and query config.
- Modify: `tests/unit_tests/gamemodules/test_scpslserver_cov.py`
  Cover SCP:SL schema metadata, query-password sync, and query-port mapping.
- Modify: `docs/servers/scpslserver.md`
  Document canonical `set` usage for `servername`, `contactemail`, `queryport`, and query admin password.
- Modify: `docs/server-templates/scpslserver/config_gameplay.txt`
  Reflect the schema-backed gameplay/query keys.

- Modify: `src/gamemodules/minecraft/bedrock.py`
  Add schema-backed canonical aliases around the Bedrock `server.properties` surface.
- Modify: `src/gamemodules/minecraft/custom.py`
  Add schema-backed canonical aliases around the Java `server.properties` surface.
- Modify: `tests/unit_tests/gamemodules/test_minecraft_bedrock_module.py`
  Cover Bedrock schema, config sync, and canonical aliases.
- Modify: `tests/unit_tests/gamemodules/test_minecraft_modules.py`
  Cover Java custom schema, config sync, and canonical aliases.
- Modify: `docs/servers/minecraft-bedrock.md`
  Document the new canonical Bedrock `set` surface.
- Modify: `docs/server-templates/minecraft-bedrock/server.properties`
  Reflect the schema-backed native Bedrock properties.
- Modify: `docs/servers/minecraft-custom.md`
  Document the new canonical Java custom `set` surface.
- Modify: `docs/server-templates/minecraft-custom/server.properties`
  Reflect the schema-backed native Java properties.

- Modify: `src/gamemodules/craftopiaserver.py`
  Add schema-backed canonical aliases and secrets for `ServerSetting.ini`.
- Modify: `src/gamemodules/mumbleserver.py`
  Add schema-backed canonical aliases and secrets for `mumble-server.ini`.
- Modify: `tests/unit_tests/gamemodules/test_craftopiaserver_cov.py`
  Cover Craftopia schema, sync, and native password/bind-address keys.
- Modify: `tests/unit_tests/gamemodules/test_mumbleserver_cov.py`
  Cover Mumble schema, sync, and canonical `maxplayers` -> `users` mapping.
- Modify: `docs/servers/craftopiaserver.md`
  Document the canonical Craftopia `set` surface.
- Modify: `docs/server-templates/craftopiaserver/ServerSetting.ini`
  Reflect the schema-backed native Craftopia keys.
- Modify: `docs/servers/mumbleserver.md`
  Document the canonical Mumble `set` surface.
- Modify: `docs/server-templates/mumbleserver/mumble-server.ini`
  Reflect the schema-backed native Mumble keys.

- Modify: `src/gamemodules/arma3server.py`
  Add schema-backed `servername` and `map`/`world` support for `server.cfg`.
- Modify: `src/gamemodules/sevendaystodie.py`
  Expand schema-backed XML config coverage beyond `port` where safely verified.
- Modify: `src/gamemodules/stnserver.py`
  Expand schema-backed text config coverage beyond `port` where safely verified.
- Modify: `src/gamemodules/wfserver.py`
  Add schema-backed `map` and `servername` aliases for `dedicated_autoexec.cfg`.
- Modify: `src/gamemodules/wreckfestserver.py`
  Expand schema-backed cfg coverage beyond `port` where safely verified.
- Modify: `tests/unit_tests/gamemodules/test_arma3server_cov.py`
  Cover Arma 3 schema and native `server.cfg` sync.
- Modify: `tests/unit_tests/gamemodules/test_sevendaystodie_cov.py`
  Cover 7DTD schema and verified XML sync keys.
- Modify: `tests/unit_tests/gamemodules/test_stnserver_cov.py`
  Cover STN schema and verified text-config sync keys.
- Modify: `tests/unit_tests/gamemodules/test_wfserver_cov.py`
  Cover Warfork schema, map discovery, and `sv_hostname`/`net_port` sync.
- Modify: `tests/unit_tests/gamemodules/test_wreckfestserver_cov.py`
  Cover Wreckfest schema and verified cfg sync keys.
- Modify: `docs/servers/arma3server.md`
  Document canonical Arma 3 `set` usage.
- Modify: `docs/server-templates/arma3server/server.cfg`
  Reflect the schema-backed Arma 3 native config keys.
- Modify: `docs/servers/sevendaystodie.md`
  Document the verified canonical 7DTD `set` surface.
- Modify: `docs/server-templates/sevendaystodie/serverconfig.xml`
  Reflect the schema-backed 7DTD native keys.
- Modify: `docs/servers/stnserver.md`
  Document the verified canonical STN `set` surface.
- Modify: `docs/server-templates/stnserver/ServerConfig.txt`
  Reflect the schema-backed STN native keys.
- Modify: `docs/servers/wfserver.md`
  Document canonical Warfork `set` usage.
- Modify: `docs/server-templates/wfserver/dedicated_autoexec.cfg`
  Reflect the schema-backed Warfork native keys.
- Modify: `docs/servers/wreckfestserver.md`
  Document the verified canonical Wreckfest `set` surface.
- Modify: `docs/server-templates/wreckfestserver/server_config.cfg`
  Reflect the schema-backed Wreckfest native keys.

- Modify: `README.md`
  Add one short wave-level example for the expanded canonical `set` surface beyond TF2.
- Modify: `DEVELOPERS.md`
  Add the wave-1 rollout guidance and module-author expectations.
- Modify: `changelog.txt`
  Add one release-facing entry for the wave-1 rollout.

### Task 1: Structured JSON Modules (`armarserver`, `rimworldtogetherserver`)

**Files:**
- Modify: `src/gamemodules/armarserver.py`
- Modify: `src/gamemodules/rimworldtogetherserver.py`
- Test: `tests/unit_tests/gamemodules/test_armarserver_cov.py`
- Test: `tests/unit_tests/gamemodules/test_rimworldtogetherserver_cov.py`
- Modify: `docs/servers/armarserver.md`
- Modify: `docs/server-templates/armarserver/server.json`
- Modify: `docs/servers/rimworldtogetherserver.md`
- Modify: `docs/server-templates/rimworldtogetherserver/ServerConfig.json`
- Modify: `docs/server-templates/rimworldtogetherserver/ServerSettings.json`

- [ ] **Step 1: Audit the verified native-key surface**

Run:

```bash
sed -n '40,120p' src/gamemodules/armarserver.py
sed -n '53,90p' src/gamemodules/rimworldtogetherserver.py
sed -n '1,160p' docs/servers/armarserver.md
sed -n '1,160p' docs/servers/rimworldtogetherserver.md
```

Expected confirmed scope:

- `armarserver`: `port`, `queryport`, `maxplayers`, `scenarioid`, `bindaddress`, `adminpassword`
- `rimworldtogetherserver`: `port` only unless the guide/template explicitly proves more; do **not** invent extra keys

- [ ] **Step 2: Write the failing tests**

Add tests like:

```python
def test_armarserver_exposes_schema_for_network_and_admin_keys():
    assert mod.config_sync_keys == (
        "port",
        "queryport",
        "maxplayers",
        "scenarioid",
        "bindaddress",
        "adminpassword",
    )
    assert mod.setting_schema["map"].storage_key == "scenarioid"
    assert mod.setting_schema["adminpassword"].secret is True
    assert "scenario" in mod.setting_schema["map"].aliases


def test_armarserver_sync_server_config_writes_bindaddress_and_adminpassword(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "configfile": "configs/server.json",
            "profilesdir": "profile",
            "port": 2001,
            "queryport": 2002,
            "maxplayers": 12,
            "scenarioid": "{scenario-guid}",
            "bindaddress": "127.0.0.1",
            "adminpassword": "topsecret",
        }
    )

    mod.sync_server_config(server)

    data = json.loads((tmp_path / "configs" / "server.json").read_text())
    assert data["a2s"]["address"] == "127.0.0.1"
    assert data["a2s"]["port"] == 2002
    assert data["game"]["passwordAdmin"] == "topsecret"
    assert data["game"]["scenarioId"] == "{scenario-guid}"


def test_rimworldtogetherserver_exposes_verified_port_only_schema():
    assert mod.config_sync_keys == ("port",)
    assert mod.setting_schema["port"].canonical_key == "port"
    assert mod.list_setting_values(DummyServer(), "port") is None
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/unit_tests/gamemodules/test_armarserver_cov.py \
  tests/unit_tests/gamemodules/test_rimworldtogetherserver_cov.py \
  -q
```

Expected: FAIL because the schema-backed surfaces and expanded config sync keys do not exist yet.

- [ ] **Step 4: Implement the schema-backed JSON modules**

Add code like:

```python
# src/gamemodules/armarserver.py
from server.settable_keys import SettingSpec

config_sync_keys = (
    "port",
    "queryport",
    "maxplayers",
    "scenarioid",
    "bindaddress",
    "adminpassword",
)

setting_schema = {
    "map": SettingSpec(
        canonical_key="map",
        aliases=("scenario", "scenarioid", "mission"),
        description="The Arma Reforger scenario to load.",
        value_type="string",
        storage_key="scenarioid",
        apply_to=("datastore", "native_config"),
    ),
    "port": SettingSpec(canonical_key="port", aliases=("gameport",), value_type="integer"),
    "queryport": SettingSpec(canonical_key="queryport", aliases=("a2sport",), value_type="integer"),
    "maxplayers": SettingSpec(canonical_key="maxplayers", aliases=("slots",), value_type="integer"),
    "bindaddress": SettingSpec(canonical_key="bindaddress", aliases=("hostip", "ip"), value_type="string"),
    "adminpassword": SettingSpec(
        canonical_key="adminpassword",
        aliases=("passwordadmin",),
        value_type="string",
        secret=True,
        apply_to=("datastore", "native_config"),
    ),
}

# keep these writes in sync_server_config(...)
"address": server.data.get("bindaddress", "0.0.0.0"),
"passwordAdmin": server.data.get("adminpassword", ""),

if key[0] == "bindaddress":
    return str(value[0])
if key[0] == "adminpassword":
    return str(value[0])
```

```python
# src/gamemodules/rimworldtogetherserver.py
from server.settable_keys import SettingSpec

setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        aliases=("gameport",),
        description="The RimWorld Together game port.",
        value_type="integer",
        apply_to=("datastore", "native_config", "launch_args"),
    )
}

def list_setting_values(server, canonical_key):
    return None
```

- [ ] **Step 5: Update the JSON-module docs and templates**

Update snippets like:

```markdown
<!-- docs/servers/armarserver.md -->
- `alphagsm myreforger set map {scenario-guid}`
- `alphagsm myreforger set adminpassword secret`
- `alphagsm myreforger set bindaddress 127.0.0.1`
```

```json
// docs/server-templates/armarserver/server.json
{
  "a2s": {
    "address": "0.0.0.0",
    "port": 2002
  },
  "game": {
    "passwordAdmin": "",
    "maxPlayers": 8,
    "scenarioId": "{scenario-guid}"
  }
}
```

```markdown
<!-- docs/servers/rimworldtogetherserver.md -->
- Verified schema-backed native key: `port`
- `alphagsm myrimworld set port 25555`
```

- [ ] **Step 6: Run the targeted tests again**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/unit_tests/gamemodules/test_armarserver_cov.py \
  tests/unit_tests/gamemodules/test_rimworldtogetherserver_cov.py \
  -q
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add \
  src/gamemodules/armarserver.py \
  src/gamemodules/rimworldtogetherserver.py \
  tests/unit_tests/gamemodules/test_armarserver_cov.py \
  tests/unit_tests/gamemodules/test_rimworldtogetherserver_cov.py \
  docs/servers/armarserver.md \
  docs/server-templates/armarserver/server.json \
  docs/servers/rimworldtogetherserver.md \
  docs/server-templates/rimworldtogetherserver/ServerConfig.json \
  docs/server-templates/rimworldtogetherserver/ServerSettings.json
git commit -m "feat: add canonical set support for json sync modules"
```

### Task 2: SCP:SL Hybrid Config Surface (`scpslserver`)

**Files:**
- Modify: `src/gamemodules/scpslserver.py`
- Test: `tests/unit_tests/gamemodules/test_scpslserver_cov.py`
- Modify: `docs/servers/scpslserver.md`
- Modify: `docs/server-templates/scpslserver/config_gameplay.txt`

- [ ] **Step 1: Audit the verified SCP:SL config surface**

Run:

```bash
sed -n '78,150p' src/gamemodules/scpslserver.py
sed -n '1,160p' docs/servers/scpslserver.md
sed -n '1,120p' docs/server-templates/scpslserver/config_gameplay.txt
```

Expected confirmed scope:

- `servername` -> `server_name`
- `contactemail` -> `contact_email`
- `queryport` -> `query_port_shift` (stored as `queryport - port`)
- `rconpassword` -> `query_administrator_password`

- [ ] **Step 2: Write the failing tests**

Add tests like:

```python
def test_scpslserver_exposes_schema_for_query_and_identity_keys():
    assert mod.config_sync_keys == ("servername", "contactemail", "queryport", "rconpassword")
    assert mod.setting_schema["servername"].storage_key == "servername"
    assert mod.setting_schema["queryport"].storage_key == "queryport"
    assert mod.setting_schema["rconpassword"].secret is True


def test_scpslserver_sync_server_config_writes_query_shift_and_password(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 7777,
            "queryport": 7780,
            "servername": "AlphaGSM SL",
            "contactemail": "ops@example.com",
            "rconpassword": "query-secret",
        }
    )

    mod.sync_server_config(server)

    cfg = (tmp_path / "config" / "7777" / "config_gameplay.txt").read_text()
    assert "server_name: AlphaGSM SL" in cfg
    assert "contact_email: ops@example.com" in cfg
    assert "query_port_shift: 3" in cfg
    assert "query_administrator_password: query-secret" in cfg
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest tests/unit_tests/gamemodules/test_scpslserver_cov.py -q
```

Expected: FAIL because the schema and expanded sync/config validation do not exist yet.

- [ ] **Step 4: Implement the SCP:SL schema-backed surface**

Add code like:

```python
from server.settable_keys import SettingSpec

config_sync_keys = ("servername", "contactemail", "queryport", "rconpassword")

setting_schema = {
    "servername": SettingSpec(
        canonical_key="servername",
        aliases=("hostname", "name"),
        value_type="string",
        apply_to=("datastore", "native_config"),
    ),
    "contactemail": SettingSpec(
        canonical_key="contactemail",
        aliases=("email", "contact_email"),
        value_type="string",
        apply_to=("datastore", "native_config"),
    ),
    "queryport": SettingSpec(
        canonical_key="queryport",
        aliases=("query_port",),
        value_type="integer",
        apply_to=("datastore", "native_config"),
    ),
    "rconpassword": SettingSpec(
        canonical_key="rconpassword",
        aliases=("querypassword", "query_administrator_password"),
        value_type="string",
        apply_to=("datastore", "native_config"),
        secret=True,
    ),
}

query_shift = int(server.data.get("queryport", server.data["port"] + 1)) - int(server.data["port"])
...
f"server_name: {server.data.get('servername', 'AlphaGSM ' + server.name)}",
f"contact_email: {server.data.get('contactemail', 'default') or 'default'}",
f"query_port_shift: {query_shift}",
f"query_administrator_password: {server.data.get('rconpassword', 'alphagsmquery')}",

if key[0] in ("servername", "contactemail", "rconpassword"):
    return str(value[0])
```

- [ ] **Step 5: Update the guide and template**

Update snippets like:

```markdown
<!-- docs/servers/scpslserver.md -->
- `alphagsm mysl set servername "AlphaGSM SCP:SL"`
- `alphagsm mysl set queryport 7780`
- `alphagsm mysl set rconpassword query-secret`
```

```text
# docs/server-templates/scpslserver/config_gameplay.txt
server_name: AlphaGSM scpsl
contact_email: default
enable_query: true
query_port_shift: 1
query_administrator_password: alphagsmquery
```

- [ ] **Step 6: Run the targeted tests again**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest tests/unit_tests/gamemodules/test_scpslserver_cov.py -q
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add \
  src/gamemodules/scpslserver.py \
  tests/unit_tests/gamemodules/test_scpslserver_cov.py \
  docs/servers/scpslserver.md \
  docs/server-templates/scpslserver/config_gameplay.txt
git commit -m "feat: add canonical set support for scpsl"
```

### Task 3: Properties Modules (`minecraft.bedrock`, `minecraft.custom`)

**Files:**
- Modify: `src/gamemodules/minecraft/bedrock.py`
- Modify: `src/gamemodules/minecraft/custom.py`
- Test: `tests/unit_tests/gamemodules/test_minecraft_bedrock_module.py`
- Test: `tests/unit_tests/gamemodules/test_minecraft_modules.py`
- Modify: `docs/servers/minecraft-bedrock.md`
- Modify: `docs/server-templates/minecraft-bedrock/server.properties`
- Modify: `docs/servers/minecraft-custom.md`
- Modify: `docs/server-templates/minecraft-custom/server.properties`

- [ ] **Step 1: Audit the verified properties-backed key surface**

Run:

```bash
sed -n '180,220p' src/gamemodules/minecraft/bedrock.py
sed -n '370,392p' src/gamemodules/minecraft/custom.py
sed -n '1,200p' docs/server-templates/minecraft-bedrock/server.properties
sed -n '1,200p' docs/server-templates/minecraft-custom/server.properties
```

Expected confirmed scope:

- `minecraft.bedrock`: `port`, `map` -> `levelname`, `gamemode`, `difficulty`, `maxplayers`, `servername`
- `minecraft.custom`: `port`, `map` -> `levelname`, `gamemode`, `difficulty`, `maxplayers`, `servername` -> `motd`

- [ ] **Step 2: Write the failing tests**

Add tests like:

```python
def test_bedrock_exposes_schema_for_map_and_identity_keys():
    assert bedrock.setting_schema["map"].storage_key == "levelname"
    assert "gamemap" in bedrock.setting_schema["map"].aliases
    assert "servername" in bedrock.setting_schema


def test_bedrock_sync_server_config_writes_levelname_and_servername(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 19132,
            "levelname": "AlphaWorld",
            "gamemode": "creative",
            "difficulty": "hard",
            "maxplayers": "20",
            "servername": "Alpha Bedrock",
        }
    )
    bedrock.sync_server_config(server)
    props = (tmp_path / "server.properties").read_text()
    assert "server-port=19132" in props
    assert "level-name=AlphaWorld" in props
    assert "server-name=Alpha Bedrock" in props


def test_custom_sync_server_config_writes_levelname_and_motd(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path),
            "port": 25565,
            "levelname": "world",
            "gamemode": "survival",
            "difficulty": "easy",
            "maxplayers": "20",
            "servername": "Alpha Java",
        }
    )
    custom.sync_server_config(server)
    props = (tmp_path / "server.properties").read_text()
    assert "level-name=world" in props
    assert "motd=Alpha Java" in props
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/unit_tests/gamemodules/test_minecraft_bedrock_module.py \
  tests/unit_tests/gamemodules/test_minecraft_modules.py \
  -q
```

Expected: FAIL because the schema-backed map/servername aliases do not exist yet.

- [ ] **Step 4: Implement the properties-backed schema**

Add code like:

```python
# src/gamemodules/minecraft/bedrock.py
from server.settable_keys import SettingSpec

setting_schema = {
    "port": SettingSpec(canonical_key="port", aliases=("gameport",), value_type="integer"),
    "map": SettingSpec(
        canonical_key="map",
        aliases=("gamemap", "level", "world"),
        storage_key="levelname",
        value_type="string",
        apply_to=("datastore", "native_config"),
    ),
    "gamemode": SettingSpec(canonical_key="gamemode", aliases=("mode",), value_type="string"),
    "difficulty": SettingSpec(canonical_key="difficulty", aliases=("skill",), value_type="string"),
    "maxplayers": SettingSpec(canonical_key="maxplayers", aliases=("slots",), value_type="integer"),
    "servername": SettingSpec(canonical_key="servername", aliases=("server-name", "name"), value_type="string"),
}

config_sync_keys = ("port", "gamemode", "difficulty", "levelname", "maxplayers", "servername")

# sync_server_config(...)
"level-name": str(server.data["levelname"]),
"server-name": str(server.data["servername"]),

if key[0] == "levelname":
    return str(value[0])
```

```python
# src/gamemodules/minecraft/custom.py
from server.settable_keys import SettingSpec

config_sync_keys = ("port", "levelname", "servername", "gamemode", "difficulty", "maxplayers")

setting_schema = {
    "port": SettingSpec(canonical_key="port", aliases=("gameport",), value_type="integer"),
    "map": SettingSpec(
        canonical_key="map",
        aliases=("gamemap", "level", "world"),
        storage_key="levelname",
        value_type="string",
        apply_to=("datastore", "native_config"),
    ),
    "servername": SettingSpec(
        canonical_key="servername",
        aliases=("motd", "name"),
        storage_key="servername",
        value_type="string",
        apply_to=("datastore", "native_config"),
    ),
    "gamemode": SettingSpec(canonical_key="gamemode", aliases=("mode",), value_type="string"),
    "difficulty": SettingSpec(canonical_key="difficulty", aliases=("skill",), value_type="string"),
    "maxplayers": SettingSpec(canonical_key="maxplayers", aliases=("slots",), value_type="integer"),
}

# sync_server_config(...)
"level-name": str(server.data.get("levelname", "world")),
"motd": str(server.data.get("servername", "AlphaGSM {}".format(server.name))),

if key in (("levelname",), ("servername",)):
    return str(value[0])
```

- [ ] **Step 5: Update the properties docs and templates**

Update snippets like:

```markdown
<!-- docs/servers/minecraft-bedrock.md -->
- `alphagsm mybedrock set gamemap AlphaWorld`
- `alphagsm mybedrock set servername "Alpha Bedrock"`
```

```properties
# docs/server-templates/minecraft-bedrock/server.properties
server-port=19132
level-name=Bedrock level
server-name=AlphaGSM bedrock
gamemode=survival
difficulty=easy
max-players=10
```

```markdown
<!-- docs/servers/minecraft-custom.md -->
- `alphagsm myjava set gamemap world`
- `alphagsm myjava set servername "Alpha Java"`
```

```properties
# docs/server-templates/minecraft-custom/server.properties
server-port=25565
level-name=world
motd=AlphaGSM java
gamemode=survival
difficulty=easy
max-players=20
```

- [ ] **Step 6: Run the targeted tests again**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/unit_tests/gamemodules/test_minecraft_bedrock_module.py \
  tests/unit_tests/gamemodules/test_minecraft_modules.py \
  -q
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add \
  src/gamemodules/minecraft/bedrock.py \
  src/gamemodules/minecraft/custom.py \
  tests/unit_tests/gamemodules/test_minecraft_bedrock_module.py \
  tests/unit_tests/gamemodules/test_minecraft_modules.py \
  docs/servers/minecraft-bedrock.md \
  docs/server-templates/minecraft-bedrock/server.properties \
  docs/servers/minecraft-custom.md \
  docs/server-templates/minecraft-custom/server.properties
git commit -m "feat: add canonical set support for minecraft modules"
```

### Task 4: INI Modules (`craftopiaserver`, `mumbleserver`)

**Files:**
- Modify: `src/gamemodules/craftopiaserver.py`
- Modify: `src/gamemodules/mumbleserver.py`
- Test: `tests/unit_tests/gamemodules/test_craftopiaserver_cov.py`
- Test: `tests/unit_tests/gamemodules/test_mumbleserver_cov.py`
- Modify: `docs/servers/craftopiaserver.md`
- Modify: `docs/server-templates/craftopiaserver/ServerSetting.ini`
- Modify: `docs/servers/mumbleserver.md`
- Modify: `docs/server-templates/mumbleserver/mumble-server.ini`

- [ ] **Step 1: Audit the verified INI-backed key surface**

Run:

```bash
sed -n '54,120p' src/gamemodules/craftopiaserver.py
sed -n '38,60p' src/gamemodules/mumbleserver.py
sed -n '1,200p' docs/server-templates/craftopiaserver/ServerSetting.ini
sed -n '1,200p' docs/server-templates/mumbleserver/mumble-server.ini
```

Expected confirmed scope:

- `craftopiaserver`: `port`, `maxplayers`, `worldname`, `serverpassword`, `bindaddress`
- `mumbleserver`: `port`, `maxplayers` -> `users`, `database`, `serverpassword`, `welcometext`

- [ ] **Step 2: Write the failing tests**

Add tests like:

```python
def test_craftopia_exposes_schema_for_world_password_and_bindaddress():
    assert mod.setting_schema["map"].storage_key == "worldname"
    assert mod.setting_schema["serverpassword"].secret is True
    assert mod.setting_schema["bindaddress"].canonical_key == "bindaddress"


def test_craftopia_sync_server_config_writes_password_and_bindaddress(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 8787,
            "maxplayers": 8,
            "worldname": "AlphaWorld",
            "serverpassword": "joinme",
            "bindaddress": "127.0.0.1",
        }
    )
    mod.sync_server_config(server)
    text = (tmp_path / "ServerSetting.ini").read_text()
    assert "serverPassword = joinme" in text
    assert "bindAddress = 127.0.0.1" in text


def test_mumbleserver_exposes_maxplayers_alias_for_users():
    assert mod.setting_schema["maxplayers"].storage_key == "users"
    assert "slots" in mod.setting_schema["maxplayers"].aliases
    assert mod.setting_schema["serverpassword"].secret is True
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/unit_tests/gamemodules/test_craftopiaserver_cov.py \
  tests/unit_tests/gamemodules/test_mumbleserver_cov.py \
  -q
```

Expected: FAIL because the schema-backed surfaces do not exist yet.

- [ ] **Step 4: Implement the INI-backed schema**

Add code like:

```python
# src/gamemodules/craftopiaserver.py
from server.settable_keys import SettingSpec

config_sync_keys = ("port", "maxplayers", "worldname", "serverpassword", "bindaddress")

setting_schema = {
    "port": SettingSpec(canonical_key="port", aliases=("gameport",), value_type="integer"),
    "maxplayers": SettingSpec(canonical_key="maxplayers", aliases=("slots",), value_type="integer"),
    "map": SettingSpec(
        canonical_key="map",
        aliases=("world", "worldname"),
        storage_key="worldname",
        value_type="string",
        apply_to=("datastore", "native_config"),
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        aliases=("password", "serverPassword"),
        value_type="string",
        apply_to=("datastore", "native_config"),
        secret=True,
    ),
    "bindaddress": SettingSpec(canonical_key="bindaddress", aliases=("bindAddress",), value_type="string"),
}

# sync_server_config(...) Host section
"serverPassword": str(server.data.get("serverpassword", "00000000")),
"bindAddress": str(server.data.get("bindaddress", "0.0.0.0")),

if key[0] in ("serverpassword", "bindaddress"):
    return str(value[0])
```

```python
# src/gamemodules/mumbleserver.py
from server.settable_keys import SettingSpec

setting_schema = {
    "port": SettingSpec(canonical_key="port", aliases=("gameport",), value_type="integer"),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        aliases=("users", "slots"),
        storage_key="users",
        value_type="integer",
        apply_to=("datastore", "native_config"),
    ),
    "database": SettingSpec(canonical_key="database", aliases=("database_path",), value_type="string"),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        aliases=("password",),
        value_type="string",
        apply_to=("datastore", "native_config"),
        secret=True,
    ),
    "welcometext": SettingSpec(canonical_key="welcometext", aliases=("welcome",), value_type="string"),
}

if key[0] == "maxplayers":
    return str(int(value[0]))
```

- [ ] **Step 5: Update the guides and templates**

Update snippets like:

```markdown
<!-- docs/servers/craftopiaserver.md -->
- `alphagsm mycraftopia set map AlphaWorld`
- `alphagsm mycraftopia set serverpassword joinme`
```

```ini
; docs/server-templates/craftopiaserver/ServerSetting.ini
[Host]
port = 8787
maxPlayerNumber = 8
serverPassword = 00000000
bindAddress = 0.0.0.0
```

```markdown
<!-- docs/servers/mumbleserver.md -->
- `alphagsm mymumble set maxplayers 32`
- `alphagsm mymumble set serverpassword secret`
```

```ini
; docs/server-templates/mumbleserver/mumble-server.ini
port=64738
users=100
serverpassword=
welcometext=Welcome to AlphaGSM
database=mumble-server.sqlite
```

- [ ] **Step 6: Run the targeted tests again**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/unit_tests/gamemodules/test_craftopiaserver_cov.py \
  tests/unit_tests/gamemodules/test_mumbleserver_cov.py \
  -q
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add \
  src/gamemodules/craftopiaserver.py \
  src/gamemodules/mumbleserver.py \
  tests/unit_tests/gamemodules/test_craftopiaserver_cov.py \
  tests/unit_tests/gamemodules/test_mumbleserver_cov.py \
  docs/servers/craftopiaserver.md \
  docs/server-templates/craftopiaserver/ServerSetting.ini \
  docs/servers/mumbleserver.md \
  docs/server-templates/mumbleserver/mumble-server.ini
git commit -m "feat: add canonical set support for ini sync modules"
```

### Task 5: Text/CFG/XML Modules (`arma3server`, `sevendaystodie`, `stnserver`, `wfserver`, `wreckfestserver`)

**Files:**
- Modify: `src/gamemodules/arma3server.py`
- Modify: `src/gamemodules/sevendaystodie.py`
- Modify: `src/gamemodules/stnserver.py`
- Modify: `src/gamemodules/wfserver.py`
- Modify: `src/gamemodules/wreckfestserver.py`
- Test: `tests/unit_tests/gamemodules/test_arma3server_cov.py`
- Test: `tests/unit_tests/gamemodules/test_sevendaystodie_cov.py`
- Test: `tests/unit_tests/gamemodules/test_stnserver_cov.py`
- Test: `tests/unit_tests/gamemodules/test_wfserver_cov.py`
- Test: `tests/unit_tests/gamemodules/test_wreckfestserver_cov.py`
- Modify: `docs/servers/arma3server.md`
- Modify: `docs/server-templates/arma3server/server.cfg`
- Modify: `docs/servers/sevendaystodie.md`
- Modify: `docs/server-templates/sevendaystodie/serverconfig.xml`
- Modify: `docs/servers/stnserver.md`
- Modify: `docs/server-templates/stnserver/ServerConfig.txt`
- Modify: `docs/servers/wfserver.md`
- Modify: `docs/server-templates/wfserver/dedicated_autoexec.cfg`
- Modify: `docs/servers/wreckfestserver.md`
- Modify: `docs/server-templates/wreckfestserver/server_config.cfg`

- [ ] **Step 1: Audit the verified text-backed key surface**

Run:

```bash
sed -n '41,90p' src/gamemodules/arma3server.py
sed -n '75,110p' src/gamemodules/sevendaystodie.py
sed -n '87,110p' src/gamemodules/stnserver.py
sed -n '75,116p' src/gamemodules/wfserver.py
sed -n '75,95p' src/gamemodules/wreckfestserver.py
```

Expected confirmed scope:

- `arma3server`: `servername`, `map` -> `world`
- `sevendaystodie`: `port` plus `servername`, `serverpassword`, and `maxplayers` only if the existing XML/template path already proves the nodes
- `stnserver`: `port` plus any additional `ServerConfig.txt` keys only if the current template/guide already proves them
- `wfserver`: `port`, `servername` -> `hostname`, `map` -> `startmap`
- `wreckfestserver`: `port` plus any additional cfg keys only if the current template/guide already proves them

- [ ] **Step 2: Write the failing tests**

Add tests like:

```python
def test_arma3server_exposes_servername_and_map_schema():
    assert mod.setting_schema["servername"].canonical_key == "servername"
    assert mod.setting_schema["map"].storage_key == "world"


def test_wfserver_exposes_map_and_servername_schema():
    assert mod.setting_schema["map"].storage_key == "startmap"
    assert mod.setting_schema["servername"].storage_key == "hostname"
    assert mod.list_setting_values(server, "map") == ["wfa1", "wfa2"]


def test_wfserver_sync_server_config_writes_hostname_and_port(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "port": 44400, "hostname": "AlphaGSM WF"})
    mod.sync_server_config(server)
    text = (tmp_path / "basewf" / "dedicated_autoexec.cfg").read_text()
    assert 'set net_port 44400' in text
    assert 'set sv_hostname "AlphaGSM WF"' in text
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/unit_tests/gamemodules/test_arma3server_cov.py \
  tests/unit_tests/gamemodules/test_sevendaystodie_cov.py \
  tests/unit_tests/gamemodules/test_stnserver_cov.py \
  tests/unit_tests/gamemodules/test_wfserver_cov.py \
  tests/unit_tests/gamemodules/test_wreckfestserver_cov.py \
  -q
```

Expected: FAIL because the schema-backed text/cfg/xml surfaces do not exist yet.

- [ ] **Step 4: Implement the text/cfg/xml schema**

Add code like:

```python
# src/gamemodules/arma3server.py
from server.settable_keys import SettingSpec

setting_schema = {
    "servername": SettingSpec(canonical_key="servername", aliases=("hostname", "name"), value_type="string"),
    "map": SettingSpec(
        canonical_key="map",
        aliases=("world", "level"),
        storage_key="world",
        value_type="string",
        apply_to=("datastore", "launch_args"),
    ),
}
```

```python
# src/gamemodules/wfserver.py
from server.settable_keys import SettingSpec

setting_schema = {
    "port": SettingSpec(canonical_key="port", aliases=("gameport",), value_type="integer"),
    "servername": SettingSpec(
        canonical_key="servername",
        aliases=("hostname", "name"),
        storage_key="hostname",
        value_type="string",
        apply_to=("datastore", "native_config"),
    ),
    "map": SettingSpec(
        canonical_key="map",
        aliases=("gamemap", "startmap", "level"),
        storage_key="startmap",
        value_type="string",
        apply_to=("datastore", "launch_args"),
    ),
}

def list_setting_values(server, canonical_key):
    if canonical_key != "map":
        return None
    ...
```

```python
# src/gamemodules/sevendaystodie.py / stnserver.py / wreckfestserver.py
# Only add schema entries for keys proven by the module's own XML/text/cfg contract.
# Keep unsupported keys out rather than guessing them.
```

- [ ] **Step 5: Update the guides and templates**

Update snippets like:

```markdown
<!-- docs/servers/arma3server.md -->
- `alphagsm myarma set servername "AlphaGSM Arma 3"`
- `alphagsm myarma set map Altis`
```

```cfg
// docs/server-templates/arma3server/server.cfg
hostname = "AlphaGSM Arma 3";
```

```markdown
<!-- docs/servers/wfserver.md -->
- `alphagsm mywf set gamemap wfa1`
- `alphagsm mywf set servername "AlphaGSM Warfork"`
```

```cfg
// docs/server-templates/wfserver/dedicated_autoexec.cfg
set net_port 44400
set sv_hostname "AlphaGSM Warfork"
```

- [ ] **Step 6: Run the targeted tests again**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/unit_tests/gamemodules/test_arma3server_cov.py \
  tests/unit_tests/gamemodules/test_sevendaystodie_cov.py \
  tests/unit_tests/gamemodules/test_stnserver_cov.py \
  tests/unit_tests/gamemodules/test_wfserver_cov.py \
  tests/unit_tests/gamemodules/test_wreckfestserver_cov.py \
  -q
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add \
  src/gamemodules/arma3server.py \
  src/gamemodules/sevendaystodie.py \
  src/gamemodules/stnserver.py \
  src/gamemodules/wfserver.py \
  src/gamemodules/wreckfestserver.py \
  tests/unit_tests/gamemodules/test_arma3server_cov.py \
  tests/unit_tests/gamemodules/test_sevendaystodie_cov.py \
  tests/unit_tests/gamemodules/test_stnserver_cov.py \
  tests/unit_tests/gamemodules/test_wfserver_cov.py \
  tests/unit_tests/gamemodules/test_wreckfestserver_cov.py \
  docs/servers/arma3server.md \
  docs/server-templates/arma3server/server.cfg \
  docs/servers/sevendaystodie.md \
  docs/server-templates/sevendaystodie/serverconfig.xml \
  docs/servers/stnserver.md \
  docs/server-templates/stnserver/ServerConfig.txt \
  docs/servers/wfserver.md \
  docs/server-templates/wfserver/dedicated_autoexec.cfg \
  docs/servers/wreckfestserver.md \
  docs/server-templates/wreckfestserver/server_config.cfg
git commit -m "feat: add canonical set support for text sync modules"
```

### Task 6: Wave-Level Docs, Changelog, And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `DEVELOPERS.md`
- Modify: `changelog.txt`

- [ ] **Step 1: Update the wave-level docs**

Add snippets like:

```markdown
<!-- README.md -->
./alphagsm mybedrock set gamemap AlphaWorld
./alphagsm mymumble set maxplayers 32
./alphagsm myreforger set adminpassword secret
```

```markdown
<!-- DEVELOPERS.md -->
- Wave-1 config-sync modules should expose `setting_schema`, `config_sync_keys`,
  `sync_server_config(server)`, and `list_setting_values(server, canonical_key)`
  where value discovery is safe.
- Canonical CLI names should resolve to module-native storage keys rather than
  leaking upstream field names directly into the shared user contract.
```

```text
# changelog.txt
- CLI: expand canonical `set` discovery and alias routing across the first
  wave of native-config-backed modules, including Minecraft, Mumble, Arma
  Reforger, SCP:SL, and additional config-sync servers.
```

- [ ] **Step 2: Run the wave-1 unit test sweep**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/unit_tests/gamemodules/test_arma3server_cov.py \
  tests/unit_tests/gamemodules/test_armarserver_cov.py \
  tests/unit_tests/gamemodules/test_craftopiaserver_cov.py \
  tests/unit_tests/gamemodules/test_minecraft_bedrock_module.py \
  tests/unit_tests/gamemodules/test_minecraft_modules.py \
  tests/unit_tests/gamemodules/test_mumbleserver_cov.py \
  tests/unit_tests/gamemodules/test_rimworldtogetherserver_cov.py \
  tests/unit_tests/gamemodules/test_scpslserver_cov.py \
  tests/unit_tests/gamemodules/test_sevendaystodie_cov.py \
  tests/unit_tests/gamemodules/test_stnserver_cov.py \
  tests/unit_tests/gamemodules/test_wfserver_cov.py \
  tests/unit_tests/gamemodules/test_wreckfestserver_cov.py \
  tests/unit_tests/server/test_settable_keys.py \
  tests/unit_tests/server/test_server.py \
  -q
```

Expected: PASS

- [ ] **Step 3: Run a quick syntax check on the touched modules**

Run:

```bash
python3 -m py_compile \
  src/gamemodules/arma3server.py \
  src/gamemodules/armarserver.py \
  src/gamemodules/craftopiaserver.py \
  src/gamemodules/minecraft/bedrock.py \
  src/gamemodules/minecraft/custom.py \
  src/gamemodules/mumbleserver.py \
  src/gamemodules/rimworldtogetherserver.py \
  src/gamemodules/scpslserver.py \
  src/gamemodules/sevendaystodie.py \
  src/gamemodules/stnserver.py \
  src/gamemodules/wfserver.py \
  src/gamemodules/wreckfestserver.py
```

Expected: no output

- [ ] **Step 4: Commit**

```bash
git add README.md DEVELOPERS.md changelog.txt
git commit -m "docs: record wave1 canonical set rollout"
```

## Self-Review

- Spec coverage:
  - wave-1 module scope: covered by Tasks 1-5
  - canonical naming conventions: covered across Tasks 1-5
  - safely mappable upstream-native expansion: covered by each task's audit step and closed expected scope
  - per-module unit coverage: covered by Tasks 1-5
  - user-facing docs/templates: covered in Tasks 1-5
  - README/DEVELOPERS/changelog: covered by Task 6
- Placeholder scan:
  - no `TODO` / `TBD` placeholders remain
  - branchy modules use explicit audit steps with expected confirmed key sets
- Type consistency:
  - canonical families use `map`, `servername`, `serverpassword`, `adminpassword`, `rconpassword`, `maxplayers`, `port`, `queryport`
  - shared schema objects consistently use `SettingSpec`
  - native config writers stay in `sync_server_config(server)`
