"""Top-level commands for isolated, local SteamCMD session profiles."""
import sys

from utils import steam_auth


def print_usage(name, file):
    """Print the intentionally password-free CLI grammar."""
    print(f'Usage: {name} steam-auth login PROFILE USERNAME', file=file)
    print(f'       {name} steam-auth status PROFILE', file=file)
    print(f'       {name} steam-auth logout PROFILE', file=file)


def run_steam_auth(name, args, *, stdout=None, stderr=None):
    """Dispatch session commands without placing account secrets in arguments."""
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    if args in (['--help'], ['-h'], ['help']):
        print_usage(name, stdout)
        return 0
    if not args or args[0] not in ('login', 'status', 'logout'):
        print_usage(name, stderr)
        return 2
    command = args[0]
    if len(args) != (3 if command == 'login' else 2):
        print_usage(name, stderr)
        return 2
    try:
        if command == 'login':
            steam_auth.login(args[1], args[2])
            print('Local SteamCMD session cached; later downloads must verify Valve access.', file=stdout)
        elif command == 'status':
            state = steam_auth.status(args[1])
            present = 'present' if state['local_session'] else 'missing'
            print(f'Local SteamCMD session: {present}. This does not verify Valve authentication or entitlement.', file=stdout)
        else:
            steam_auth.logout(args[1])
            print('Selected local SteamCMD session deleted; this does not revoke sessions at Valve.', file=stdout)
    except steam_auth.SteamAuthError as error:
        print(str(error), file=stderr)
        return 1
    except OSError:
        print('Cannot access the local SteamCMD profile safely; check ownership and permissions.', file=stderr)
        return 1
    return 0
