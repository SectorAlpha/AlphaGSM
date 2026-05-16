Waterfall uses config.yml as its main configuration, but AlphaGSM does not
currently synthesize the full proxy schema from datastore values in this module.

Use the upstream generated config.yml as the authoritative base and then align
listener ports or proxy metadata with your AlphaGSM settings.