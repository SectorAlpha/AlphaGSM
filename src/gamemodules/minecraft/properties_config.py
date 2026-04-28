from utils.gamemodules.minecraft.properties_config import *  # noqa: F401,F403


def get_start_command(server):
	"""Properties-config helper is not a runnable gamemodule."""
	raise NotImplementedError("Minecraft properties_config helper is not runnable")