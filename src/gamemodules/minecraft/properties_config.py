from utils.gamemodules.minecraft.properties_config import *  # noqa: F401,F403


def get_start_command(server):
	"""Properties-config helper is not a runnable gamemodule."""
	raise NotImplementedError("Minecraft properties_config helper is not runnable")


def get_runtime_requirements(server):
	"""Properties-config helper does not provide runtime metadata."""
	raise NotImplementedError("Minecraft properties_config helper is not runnable")


def get_container_spec(server):
	"""Properties-config helper does not provide a container spec."""
	raise NotImplementedError("Minecraft properties_config helper is not runnable")