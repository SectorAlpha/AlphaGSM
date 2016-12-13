# AlphaGSM

This is the Sector Alpha Game Server Manager.

This tool runs game servers using screen to manage the sessions and provides
tools to control them in a consistent way and to manage many servers at once.
This also contains code to share downloads and if possible the actual files
between multiple installs.

In short, setting up and installing a game server is as easy as

  `alphagsm mymcserver create minecraft` 
  `alphagsm mymcserver setup`
  `alphagsm mymcserver start`

## Setup

For a single user configuration AlphaGSM will run out of the box. Simply download the code, copy alphagsm.conf-template to alphagsm.conf and 
run the alphagsm executable. Edit alphagsm.conf if you wish to alter the default setup.

Be sure to check out the dependancies and to look at the examples below to get your first game server running.

For changing users on multi-user setups, sudo is used so all protected permissions are controlled
using sudo.

The public script is alphagsm. This can either by run using it's full or relative
path or for ease of use can be installed in bin/ (or ~/bin/) using a symlink (It
can't be physically moved as other paths are resolved relative to it's true 
location).

For help using it run alphagsm --help or see the examples below.

For help editing and contributing see the documentation in the source code or the
pydoc output, especially for the modules "server.gamemodules" and
"downloader.downloadermodules".

## Community

If you have a question for the community and developers, you will
always be welcome to contact us by these various means of communication.

* IRC: sasha.sector-alpha.net, channel #sector-alpha
* WebIRC: http://webirc.sector-alpha.net/
* Discord: https://discordapp.com/invite/p5PtHat
* Twitter: https://twitter.com/sectoralpha
* Steam: http://steamcommunity.com/groups/sector-alpha

The plans are also being discussed on the sector alpha wiki at
http://wiki.sector-alpha.net/index.php?title=AlphaGSM.

## Dependencies

Main dependancies

  python3
  screen
  crontab
  python3-crontab
  sudo (for multi user/shared downloads support)

SteamCMD dependencies

  lib32gcc1 or libstdc++ or libstdc++.i686 

  e.g ubuntu, ib32stdc++6
  
for Ubuntu/Debian, redhat/centos and redhat/centos 64 bit respectively (pick one).
see https://developer.valvesoftware.com/wiki/SteamCMD#Linux for more details.

# Examples

Example of setting up of a Minecraft vanilla server

  `alphagsm mymcserver create minecraft setup`
  `alphagsm mymcserver start`

Example of setting up a CS:GO server

  `alphagsm mycsgo create csgo`
  `alphagsm mycsgo setup`
  `alphagsm mycsgo start`

Example of updating the CS:GO server (A specific command for updating the server files). These commands are not specific to all game servers (e.g Minecraft).

  `alphagsm mycsgo update`
  `alphagsm mycsgo update -v -r`

Where the -v flag requests the validation of files, and -r will restart your server once the update has been done.

This will create a new minecraft server called mymcserver and set it up
asking you for which version and port to use and any other info it needs.
The second command will (assuming the setup succeded) start the server.

There are various servers available "minecraft" defaults to vanilla minecraft
which has the full name is minecraft.vanilla. There is also minecraft.custom
and minecraft.tekkit and many more to come including Terraria, Steam games
and team speak

To stop the server 

  `alphagsm mymcserver stop`

To backup

  `alphagsm mymcserver backup`

which will use the default backup settings for the server. For details of how
configure backups and setup regular backups please see the full help by 
running `alphagsm --help`.
