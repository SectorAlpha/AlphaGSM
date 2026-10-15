"""Capability-aware permission prompts for exact local binding previews."""

from server.public_query import PROFILES
from .config import ConfigError
from .contracts import ACTIONS


def publication_choice(game, approved, explicit):
    if game not in PROFILES:
        print("Public listing unavailable for " + game + "; private binding and management are supported.")
        if explicit is True:
            raise ConfigError("This game has no supported public query profile")
        return False
    if explicit is not None:
        return explicit
    response = input("Publish this server in the public directory? [" + ("keep yes" if approved else "no") + "]: ").strip().lower()
    if not response:
        return approved
    if response not in ("y", "yes", "n", "no"):
        raise ConfigError("Publication requires yes or no")
    return response in ("y", "yes")


def actions_choice(approved, explicit):
    if explicit is not None:
        return explicit
    response = input("Allowed remote actions (status start stop restart) [" + (" ".join(approved) or "none") + "]: ").strip()
    if not response:
        return list(approved)
    actions = [] if response == "none" else response.split()
    if len(set(actions)) != len(actions) or any(action not in ACTIONS for action in actions):
        raise ConfigError("Only status, start, stop and restart are allowed")
    return actions


def require_capabilities(value, publication, actions):
    """Known enrollments cannot approve a capability they did not receive."""
    if value['installation_id'] is None:
        return
    if publication and not value['reporting']:
        raise ConfigError("Publication requires an enrolled reporting credential")
    if actions and not value['management']:
        raise ConfigError("Management actions require an enrolled management credential")


def permissions(game, previous, value, options):
    publication = previous['publication'] if previous else False
    actions = previous['actions'] if previous else []
    require_capabilities(value, options.publish if options.publish is not None else publication,
                         options.actions if options.actions is not None else actions)
    unknown = value['installation_id'] is None
    publication = publication_choice(game, publication, options.publish) if (
        unknown or value['reporting'] or game not in PROFILES) else False
    actions = actions_choice(actions, options.actions) if unknown or value['management'] else []
    return publication, actions


def next_steps(value):
    available = ['agent enable-' + scope for scope in ('reporting', 'management') if value[scope]]
    if available:
        print("Next: " + " and/or ".join(available) + " when ready; then agent run.")
    else:
        print("This enrollment has no reporting or management credential available.")
