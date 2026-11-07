"""Game-specific platform declarations and native executable format preflight.

Declarations are optional evidence, not a guess based on the manager's OS.
Only the executable actually launched is inspected: explicit Wine/Proton or
interpreter commands remain responsible for their payload arguments.
"""
from pathlib import Path
import os
import shutil

from utils.platform_info import PLATFORM, ARCH


class PlatformCompatibilityError(Exception):
    """The selected game payload cannot run through the selected runtime."""


def _normalize(value):
    aliases = {'win32': 'windows', 'darwin': 'macos', 'amd64': 'x86_64',
               'x64': 'x86_64', 'aarch64': 'arm64', 'i386': 'x86', 'i686': 'x86'}
    value = str(value).lower()
    return aliases.get(value, value)


def _values(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (tuple, list, set)) or not all(isinstance(item, str) for item in value):
        raise PlatformCompatibilityError('Platform declarations must contain strings.')
    return sorted({_normalize(item) for item in value})


def get_platform_requirements(server):
    """Read optional, configuration-dependent process/docker requirements."""
    hook = getattr(server.module, 'get_platform_requirements', None)
    try:
        value = hook(server) if callable(hook) else {}
    except Exception as ex:  # pylint: disable=broad-exception-caught
        raise PlatformCompatibilityError('Unable to inspect game platform requirements.') from ex
    if not isinstance(value, dict):
        raise PlatformCompatibilityError('get_platform_requirements must return a mapping.')
    for runtime, requirements in value.items():
        if runtime not in ('process', 'docker') or not isinstance(requirements, dict):
            raise PlatformCompatibilityError('Platform requirements must map process/docker to declarations.')
    return value


def normalized_platform_requirements(server):
    """Merge hook/static declarations once for lifecycle checks and inventories."""
    requirements = get_platform_requirements(server)
    declared = requirements.get('process', {})
    platforms = _values(declared.get('platforms', getattr(server.module, 'process_platforms',
                        getattr(server.module, 'supported_platforms', None))))
    architectures = _values(declared.get('architectures', getattr(server.module, 'process_architectures',
                            getattr(server.module, 'supported_architectures', None))))
    container_os = requirements.get('docker', {}).get('operating_system')
    if container_os is not None and (not isinstance(container_os, str)
                                     or _normalize(container_os) not in ('linux', 'windows')):
        raise PlatformCompatibilityError('Docker operating_system must be linux or windows.')
    return {'process': {'platforms': platforms, 'architectures': architectures},
            'docker': {'operating_system': _normalize(container_os) if container_os is not None else None}}


def platform_declaration(server, *, host=None, architecture=None):
    """Describe declared process support while keeping missing evidence unknown."""
    host, architecture = _normalize(host or PLATFORM), _normalize(architecture or ARCH)
    declared = normalized_platform_requirements(server)['process']
    platforms, architectures = declared['platforms'], declared['architectures']
    supported = None
    if platforms is not None or architectures is not None:
        supported = ((platforms is None or host in platforms)
                     and (architectures is None or architecture in architectures))
    return {'host': host, 'architecture': architecture, 'supported': supported,
            'declared_platforms': platforms, 'declared_architectures': architectures}


def validate_declared_platform(server, *, host=None, architecture=None, windows_compatibility=False):
    """Reject known incompatible game declarations before installing or starting."""
    report = platform_declaration(server, host=host, architecture=architecture)
    if report['supported'] is not False:
        return report
    platforms = report['declared_platforms']
    architectures = report['declared_architectures']
    architecture_matches = architectures is None or report['architecture'] in architectures
    if (windows_compatibility and report['host'] == 'linux' and platforms and 'windows' in platforms
            and architecture_matches):
        report['supported'] = True
        report['compatibility_layer'] = 'wine-proton'
        return report
    target = '/'.join(platforms or ['any OS']) + ' (' + '/'.join(architectures or ['any CPU']) + ')'
    raise PlatformCompatibilityError(
        f"Game server {server.name} requires {target}; this host is {report['host']} "
        f"({report['architecture']}). Select a supported game build or use a compatible Docker runtime."
    )


def _executable_path(command, cwd):
    name = os.fspath(command[0])
    path = Path(name)
    if not path.is_absolute() and ('/' in name or '\\' in name):
        path = Path(cwd or os.getcwd()) / path
    elif not path.is_absolute():
        # Relative PATH entries are evaluated in the child's working directory
        # on POSIX; inspecting the manager's cwd could validate the wrong file.
        search_path = os.environ.get('PATH', os.defpath)
        if os.name != 'nt':
            search_path = os.pathsep.join(str(Path(cwd or os.getcwd()) / entry)
                                          if not os.path.isabs(entry) else entry
                                          for entry in search_path.split(os.pathsep))
        resolved = shutil.which(name, path=search_path)
        if not resolved:
            return None
        path = Path(resolved)
    return path if path.is_file() else None


def _format_platform(path):
    with path.open('rb') as handle:
        magic = handle.read(4)
    if magic == b'\x7fELF':
        return 'linux', 'ELF'
    if magic[:2] == b'MZ':
        return 'windows', 'PE/Windows'
    if magic in (b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf',
                 b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
                 b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca'):
        return 'macos', 'Mach-O'
    if magic[:2] == b'#!':
        return None, 'script'
    return None, None


def validate_process_command(server, command, cwd=None, *, host=None, architecture=None,
                             windows_compatibility=False):
    """Check the final native launch command without executing its program."""
    if not isinstance(command, (tuple, list)) or not command:
        raise PlatformCompatibilityError('A process launch requires an executable argument list.')
    host = _normalize(host or PLATFORM)
    executable = _executable_path(command, cwd)
    wrapper = Path(os.fspath(command[0])).name.lower()
    wine = host == 'linux' and (windows_compatibility or wrapper in ('wine', 'wine64', 'wine-preloader', 'proton'))
    report = validate_declared_platform(server, host=host, architecture=architecture,
                                        windows_compatibility=wine)
    if executable is None:
        return report  # Preserve normal missing-executable/dependency handling.
    platform, format_name = _format_platform(executable)
    if platform is not None and platform != host:
        hint = ('Use an explicit Wine/Proton command or a compatible Docker runtime.'
                if platform == 'windows' and host == 'linux'
                else 'Select a build for this OS or use a compatible Docker runtime.')
        raise PlatformCompatibilityError(
            f'Cannot launch {format_name} executable {executable.name} on {host}. {hint}')
    if format_name == 'script' and host == 'windows':
        raise PlatformCompatibilityError(
            f'Cannot launch Unix script {executable.name} directly on Windows. '
            'Use a supported interpreter command or a compatible Docker runtime.')
    return report
