Valheim does not use a single static config file in this module.
AlphaGSM builds the server launch arguments directly from datastore values.

Default module-managed values:
- servername: AlphaGSM <server name>
- worldname: <server name>
- serverpassword: alphagsm
- public: 0
- port: 2456
- exe_name: valheim_server.x86_64

Equivalent launch shape:
./valheim_server.x86_64 \
	-name "AlphaGSM Server" \
	-port 2456 \
	-world "world" \
	-password "alphagsm" \
	-savedir ./worlds \
	-public 0 \
	-batchmode \
	-nographics