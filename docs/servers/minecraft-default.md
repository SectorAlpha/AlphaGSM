# minecraft.DEFAULT

`minecraft.DEFAULT` is an alias for [`minecraft.vanilla`](servers/minecraft-vanilla.md).

```bash
alphagsm myserver create minecraft.DEFAULT
```

See the [minecraft.vanilla](minecraft-vanilla.md) guide for full details.

## Resetting the World

Stop the server, then run `alphagsm mymc reset-world` (or `wipe`). AlphaGSM
lists the world data to delete and asks for confirmation. Add `-Y` to skip the
prompt. Run `start` afterwards to generate a fresh world.

See [world creation and reset](../world-management.md) for exactly which files
are removed and the supported layouts.
