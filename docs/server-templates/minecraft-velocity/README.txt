Velocity uses velocity.toml as its main configuration, but AlphaGSM does not
currently synthesize the full proxy schema from datastore values in this module.

Use the upstream generated velocity.toml as the authoritative base and then
align bind addresses, ports, and proxy metadata with your AlphaGSM settings.