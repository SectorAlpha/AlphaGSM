"""Versioned, redacted server diagnostics and installation provenance records."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
from importlib import import_module
import io
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit
import zipfile

import server.runtime as runtime_module
from server.settable_keys import redact_value
from server.capabilities import get_module_capabilities
from utils.state_io import atomic_write_text


SCHEMA_VERSION = 1
_SECRET_KEY = re.compile(r'password|passwd|secret|token|credential|authorization|apikey|api_key', re.I)
_URL = re.compile(r'https?://[^\s\"\'<>]+')
_MAX_HASH_BYTES = 512 * 1024 * 1024


def get_version():
    """Load the application version after server imports finish."""
    return import_module('core.version').get_version()


def _safe_url(value):
    """Keep source identity without URL userinfo, queries, or fragments."""
    try:
        parts = urlsplit(str(value))
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in ('https', 'http') or not parts.hostname:
        return None
    host = parts.hostname
    if ':' in host:
        host = '[' + host + ']'
    if port:
        host += ':' + str(port)
    return urlunsplit((parts.scheme, host, parts.path, '', ''))


def redact_diagnostic(server, payload):
    """Redact schema-backed secrets, sensitive keys/argv and signed URL data."""
    secrets = set()
    schema = server.get_setting_schema()
    for spec in schema.values():
        value = server.data.get(spec.storage_key or spec.canonical_key)
        if redact_value(spec, value) != value and isinstance(value, str) and value:
            secrets.add(value)
    for key, value in server.data.items():
        if _SECRET_KEY.search(str(key)) and isinstance(value, str) and value:
            secrets.add(value)

    patterns = [re.escape(secret) if len(secret) >= 4 else r'(?<!\w)' + re.escape(secret) + r'(?!\w)'
                for secret in sorted(secrets, key=len, reverse=True)]
    secret_pattern = re.compile('|'.join(patterns)) if patterns else None

    def clean(value):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key == 'status' and isinstance(item, str) and item in ('ok', 'failed', 'passed', 'unknown', 'skipped', 'unavailable'):
                    result[key] = item  # Schema enums are not credential-bearing data.
                else:
                    result[key] = '<redacted>' if _SECRET_KEY.search(str(key)) else clean(item)
            return result
        if isinstance(value, (list, tuple)):
            result = []
            hide_next = False
            for item in value:
                if hide_next:
                    result.append('<redacted>')
                    hide_next = False
                elif isinstance(item, str) and item.startswith(('-', '+')) and _SECRET_KEY.search(item.split('=', 1)[0]):
                    key, separator, _ = item.partition('=')
                    result.append(key + '=<redacted>' if separator else key)
                    hide_next = not separator
                else:
                    result.append(clean(item))
            return result
        if isinstance(value, str):
            if secret_pattern is not None:
                value = secret_pattern.sub('<redacted>', value)
            return _URL.sub(lambda match: _safe_url(match.group()) or '<redacted-url>', value)
        return value

    return clean(payload)


def _runtime_checks(snapshot):
    """Translate runtime errors and dependency checks to stable categories."""
    checks = []
    for key, value in snapshot.items():
        if key.endswith('_error'):
            checks.append({'id': key, 'category': 'runtime', 'status': 'failed', 'message': str(value)})
    for requirement in snapshot.get('host_requirements', []):
        checks.append({'id': 'host_dependency.' + str(requirement.get('name', requirement.get('display_name', 'unknown'))),
                       'category': 'dependency', 'status': 'passed' if requirement.get('ok') else 'failed',
                       'message': requirement.get('error') or requirement.get('display_name', 'Host dependency')})
    if snapshot.get('host_requirements_ok') is False and not any(item['status'] == 'failed' for item in checks):
        checks.append({'id': 'host_requirements', 'category': 'dependency', 'status': 'failed',
                       'message': 'Host dependencies are not satisfied'})
    if snapshot.get('image_present') is False:
        checks.append({'id': 'container_image', 'category': 'runtime', 'status': 'unknown',
                       'message': 'Container image is not local; startup may pull it'})
    return checks


def _provider_checks(server):
    """Check declared provider keys without including their values."""
    hook = getattr(server.module, 'get_provider_requirements', None)
    if not callable(hook):
        return []
    checks = []
    for index, requirement in enumerate(hook(server) or []):
        keys = requirement.get('keys', ())
        missing = [key for key in keys if not str(server.data.get(key, '')).strip()]
        checks.append({'id': f'provider_requirement.{index}', 'category': 'provider',
                       'status': 'failed' if missing or not keys else 'passed',
                       'message': str(requirement.get('summary', 'Provider requirement')),
                       'missing_keys': missing})
    return checks


def get_diagnostic_report(server):
    """Return schema v1 even when runtime/provider inspection fails before start."""
    checks = []
    # Module hooks occasionally print; those messages must not corrupt JSON or
    # bypass redaction. Structured failures remain available in the report.
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        try:
            snapshot = runtime_module.get_runtime_doctor_report(server)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            snapshot = {'inspection_error': str(exc)}
        checks.extend(_runtime_checks(snapshot))
        try:
            checks.extend(_provider_checks(server))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            checks.append({'id': 'provider_inspection', 'category': 'provider',
                           'status': 'failed', 'message': str(exc)})
    install_dir = server.data.get('dir')
    if install_dir and not Path(install_dir).is_dir():
        checks.append({'id': 'install_directory', 'category': 'installation', 'status': 'failed',
                       'message': 'Configured installation directory does not exist'})
    report = {'schema_version': SCHEMA_VERSION, 'server': server.name,
              'module': server.data.get('module'), 'runtime': snapshot, 'checks': checks,
              'capabilities': get_module_capabilities(server),
              'status': 'failed' if any(item['status'] == 'failed' for item in checks) else 'ok'}
    return redact_diagnostic(server, report)


def _artifact_digest(evidence):
    """Hash only an explicitly identified, reasonably sized downloaded artifact."""
    path_value = evidence.get('artifact_path')
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_file() or path.stat().st_size > _MAX_HASH_BYTES:
        return None
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _installed_jar_evidence(server):
    """Read bounded version metadata from a downloaded Minecraft server jar."""
    executable = server.data.get('exe_name', '')
    if not (str(server.data.get('module', '')).startswith('minecraft.')
            and server.data.get('current_url') and executable.endswith('.jar') and server.data.get('dir')):
        return {}
    path = Path(server.data['dir']) / executable
    if not path.is_file() or path.stat().st_size > _MAX_HASH_BYTES:
        return {}
    evidence = {'artifact_path': str(path)}
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.getinfo('version.json').file_size <= 1024 * 1024:
                metadata = json.loads(archive.read('version.json'))
                if isinstance(metadata, dict) and isinstance(metadata.get('id'), str):
                    evidence['game_version'] = metadata['id']
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        pass  # Custom jars need not expose Mojang's version metadata.
    return evidence


def _steam_app_builds(server):
    """Read small installed Steam manifests without scanning game content."""
    if not server.data.get('dir'):
        return []
    builds = []
    for path in sorted((Path(server.data['dir']) / 'steamapps').glob('appmanifest_*.acf')):
        if path.stat().st_size > 1024 * 1024:
            continue
        text = path.read_text(encoding='utf-8', errors='replace')
        app_id = re.search(r'"appid"\s+"(\d+)"', text)
        build_id = re.search(r'"buildid"\s+"(\d+)"', text)
        if app_id and build_id:
            builds.append({'app_id': app_id.group(1), 'build_id': build_id.group(1)})
    return builds


def build_installation_provenance(server, action):
    """Describe observed installation evidence; configured versions are not facts."""
    hook = getattr(server.module, 'get_installation_provenance', None)
    evidence = _installed_jar_evidence(server)
    if callable(hook):
        evidence.update(hook(server) or {})
    image_digest = evidence.get('image_digest')
    if not isinstance(image_digest, str) or not re.fullmatch(r'sha256:[a-fA-F0-9]{64}', image_digest):
        image_digest = None
    version = evidence.get('game_version') or server.data.get('installed_version')
    source = evidence.get('source_url') or server.data.get('current_url')
    report = {'schema_version': SCHEMA_VERSION, 'server': server.name, 'module': server.data.get('module'),
              'action': action, 'recorded_at': datetime.now(timezone.utc).isoformat(),
              'alphagsm_version': get_version(), 'game_version': version,
              'source_url': _safe_url(source) if source else None,
              'artifact_sha256': _artifact_digest(evidence), 'image_digest': image_digest,
              'steam_app_builds': _steam_app_builds(server)}
    return redact_diagnostic(server, report)


def record_installation_provenance(server, action):
    """Atomically replace the successful-install record beside the server state."""
    filename = getattr(server.data, 'filename', None)
    if not filename:
        return None  # In-memory API consumers have no persistent state location.
    state_path = Path(filename)
    directory = state_path.parent / '.provenance'
    directory.mkdir(mode=0o700, exist_ok=True)
    path = directory / state_path.with_suffix('.installation.json').name
    payload = build_installation_provenance(server, action)
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + '\n', mode=0o600)
    return path
