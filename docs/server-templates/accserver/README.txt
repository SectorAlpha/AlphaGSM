Assetto Corsa Competizione uses a cfg directory with multiple JSON files.
AlphaGSM tracks the directory layout and launch path, but it does not generate the
full ACC JSON schema from datastore values in this module.

Module-known defaults:
- configdir: cfg
- configfile: configuration.json
- settingsfile: settings.json
- eventfile: event.json
- eventrulesfile: eventRules.json
- connectionfile: assistRules.json
- port: 9231

Use the game's generated cfg files or upstream ACC server examples as the base,
then adjust them alongside AlphaGSM's setup and start options.