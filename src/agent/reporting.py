"""Latest metadata reconciliation and durable sequence, with no console/query data."""

from .contracts import validate_report, validate_policy


def policy_snapshot(cfg):
    value = {
        "schema_version": 1,
        "installation_id": cfg["installation_id"],
        "policy_version": cfg["policy_version"],
        "bindings": [
            {
                "binding_id": id_,
                "binding_epoch": b["epoch"],
                "allowed_actions": b["actions"] if cfg["management_enabled"] else [],
            }
            for id_, b in cfg["bindings"].items()
        ],
    }
    return validate_policy(value)


def report_snapshot(config, runtime):
    cfg = config.sequence()
    selected = []
    for binding_id, binding in cfg["bindings"].items():
        metadata = dict(binding["metadata"])
        state = "unknown"
        try:
            # Metadata is a local publication choice. Do not call module query,
            # info, console, RCON, or datastores containing private fields.
            with runtime.lock(binding["tag"]):
                state = runtime.state(binding["tag"])
                metadata = runtime.metadata(binding["tag"], metadata)
        except Exception:
            pass
        selected.append(
            {
                "binding_id": binding_id,
                "binding_epoch": binding["epoch"],
                "publication": binding["publication"] and cfg["reporting_enabled"],
                "runtime_state": state,
                "allowed_actions": binding["actions"] if cfg["management_enabled"] else [],
                **metadata,
            }
        )
    return validate_report(
        {
            "schema_version": 1,
            "installation_id": cfg["installation_id"],
            "sequence": cfg["sequence"],
            "policy_version": cfg["policy_version"],
            "bindings": selected,
        }
    )
