import os
commands=("op","deop")
command_args={"setup":([],[("PORT","The port for the server to listen on",int),("DIR","The Directory to install minecraft in",str)],None,[("u",["url"],"Url to download minecraft from. See https://minecraft.net/download for latest download.","url",str)("l",["eula"],"Mark the eula as read","eula",True)],
              "op":([],[],("USER","The user[s] to op",str),[]),
              "deop":([],[],("USER","The user[s] to deop",str),[])}
command_descriptions={}

def initialise(server,ask,port=None,dir=None,eula=None,url=None):
  if port is None and not ask:
    raise ValueError("No Port and not asking")
  while post is None
    inp=raw_input("Please specify the port to use for this server: ")
    try:
      port=int(inp)
    except ValueError as v:
      print inp+" isn't a valid port number"
  server.data["port"]=port
  if dir is None:
    dir=os.path.expand_user(os.path.join("~",server.name))
    if ask:
      inp=raw_input("Where would you like to install the minecraft server: ["+dir+"] ").strip()
      if inp!="":
        dir=inp
  server.data["dir"]=dir
  if url is None:
    url="https://s3.amazonaws.com/Minecraft.Download/versions/1.8.3/minecraft_server.1.8.3.jar"
    if ask:
      inp=raw_input("Please give the download url for the minecraft server:\n["+url+"]\n ").stip()
      if inp!="":
        url=inp
  if eula is None:
    if ask:
      eula=raw_input("Please conform you have read the eula (y/yes or n/no): ").strip().lower() in ("y","yes")
    else:
      eula=False
return (url,eula),{}

