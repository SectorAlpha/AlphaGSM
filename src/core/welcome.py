"""Optional interactive guidance; existing commands retain their own consent flows."""

import os
from pathlib import Path
import re
import shlex
import sys

from . import welcome_state


def _interactive():
    return all(getattr(stream, 'isatty', lambda: False)()
               for stream in (sys.stdin, sys.stdout))


def _yes(prompt):
    return input(prompt + ' [y/N]: ').strip().lower() in ('y', 'yes')


def _command(name, *args):
    return shlex.join([name, *args])


def _remember(choice):
    try:
        welcome_state.remember(choice)
    except OSError as exc:
        print('Could not remember tour preference: %s' % exc, file=sys.stderr)
        return 1
    return 0


def _commands(name, tag='my-server'):
    print('\nEveryday flow: create -> setup -> start -> status/query/info -> stop.')
    for command in ('setup', 'start', 'status', 'query', 'info --json', 'doctor', 'stop'):
        print('  ' + _command(name, tag, *command.split()))
    print('Help: ' + _command(name, '--help'))
    print('Replay this tour: ' + _command(name, '--welcome'))


def _create(name, execute):
    from server import server as server_module
    from .server_names import RESERVED_SERVER_NAMES
    from utils.state_io import state_lock

    catalogue = server_module.MODULE_CATALOG
    while True:
        game = input('Game module (minecraft.vanilla, tf2, ? to list; Enter to cancel): ').strip().lower()
        if not game:
            return 0
        if game == '?':
            print('\n'.join(catalogue.canonical_modules))
            continue
        game = catalogue.resolve(game)
        if game in catalogue.canonical_modules:
            break
        print('Unknown game module. Enter ? to list the available modules.')
    tag = input('Local server name (Enter to cancel): ').strip()
    if not tag:
        return 0
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', tag):
        print('Use a local name containing letters, digits, dots, underscores or hyphens.')
        return 0
    if tag.isdigit() or tag.lower() in RESERVED_SERVER_NAMES | {'all', 'version'}:
        print('That name is reserved for a command or server selector. Choose a different local name.')
        return 0
    path = Path(server_module.DATAPATH) / (tag + '.json')
    if os.path.lexists(path):
        print('That server name already exists. Existing servers are not replaced by this tour.')
        return 0
    print('\nCreate a local server record: ' + _command(name, tag, 'create', game))
    print('Setup/downloads require a separate confirmation. The game will not start automatically.')
    if not _yes('Create this server record?'):
        return 0
    with state_lock(path):
        if os.path.lexists(path):
            print('That server name was created by another command. Nothing was replaced.')
            return 1
        result = execute(name, [tag, 'create', game])
    if result:
        return result
    print('Next: ' + _command(name, tag, 'setup'))
    if _yes('Run setup now? It may download game files/install a runtime and asks for its settings'):
        result = execute(name, [tag, 'setup'])
        if result:
            print('Setup did not finish. Retry with: ' + _command(name, tag, 'setup'))
            return result
    _commands(name, tag)
    return 0


def _connect(name, execute):
    print('\nOptional Sector Alpha connection: get the enrollment code from your')
    print('account at https://sector-alpha.net. The agent uses')
    print('https://alphagsm-api.sector-alpha.net for every operation and does not')
    print('ask you to choose a host. Another provider is used only with --origin.')
    print('This tour opens agent setup. It previews servers and asks before saving.')
    print('This tour never enables reporting or management. Existing choices are preserved.')
    print('After this wizard, reporting needs a separate explicit agent enable-reporting command.')
    if _yes('Open the Sector Alpha enrollment/binding wizard?'):
        return execute(name, ['agent', 'setup'])
    return 0


def _tour(name, execute):
    print('\nWelcome to AlphaGSM. Manage game servers locally; Sector Alpha is optional.')
    print('Taking this tour does not enable remote reporting, public listings or management.')
    while True:
        print('\n1. Create/configure a game server\n2. Everyday commands\n3. Optional Sector Alpha connection')
        choice = input('Choose 1, 2 or 3; Enter or s finishes the tour: ').strip().lower()
        if choice in ('', 's', 'skip'):
            return _remember('completed')
        if choice == '1':
            result = _create(name, execute)
        elif choice == '2':
            _commands(name)
            result = 0
        elif choice == '3':
            result = _connect(name, execute)
        else:
            print('Choose 1, 2, 3, or Enter to finish.')
            continue
        if result:
            return result


def dispatch(name, args, execute):
    """Return None for ordinary dispatch, otherwise handle an explicit/first-run tour."""
    if args == ['--welcome', '--help']:
        print('Run %s --welcome to replay the optional tour; --skip-welcome remembers an opt-out.' % name)
        return 0
    if args and args not in (['--welcome'], ['--skip-welcome']):
        print('Usage: %s [--welcome | --skip-welcome]' % name, file=sys.stderr)
        return 2
    try:
        if args == ['--skip-welcome']:
            result = _remember('skipped')
            if not result:
                print('Tour skipped. Replay any time with: ' + _command(name, '--welcome'))
            return result
        if not _interactive():
            if args:
                print('The tour needs interactive input and output. Use --help for scripted commands.', file=sys.stderr)
                return 2
            return None
        if not args:
            if welcome_state.seen():
                return None
            if not _yes('First time using AlphaGSM? Start the optional setup tour? Enter skips it'):
                return _remember('skipped')
        return _tour(name, execute)
    except EOFError:
        print('\nTour cancelled; no further commands run. Replay with ' + _command(name, '--welcome'))
        return 0
    except KeyboardInterrupt:
        print('\nTour cancelled; no further commands run. Replay with ' + _command(name, '--welcome'))
        return 130
    except OSError as exc:
        print('Tour unavailable: %s' % exc, file=sys.stderr)
        return 1
