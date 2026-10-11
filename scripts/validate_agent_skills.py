"""Check repository skill metadata, Markdown references and native discovery."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml


class UniqueKeyLoader(yaml.SafeLoader):  # pylint: disable=too-many-ancestors
    """Reject ambiguous metadata rather than silently using the last value."""


def _unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate YAML key: {key}", key_node.start_mark
            )
        result[key] = loader.construct_object(value_node)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping
)
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\n]+)\)")
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def _without_fences(document):
    lines = []
    fence = None
    for line in document.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[marker.end():].strip():
                fence = None
        elif fence is None:
            lines.append(line)
    return "\n".join(lines)


def _links(document, errors=None):
    """Read inline Markdown destinations, excluding illustrative fenced code."""
    text = _without_fences(document)
    for target in LINK.findall(text):
        target = target.strip()
        if target.startswith("<"):
            target = target[1:].split(">", 1)[0]
        else:
            target = re.split(r"\s+[\"']", target, maxsplit=1)[0]
        try:
            url = urlsplit(target)
        except ValueError:
            if errors is not None:
                errors.append(f"invalid Markdown URL: {target}")
            continue
        if not url.scheme and not url.netloc and url.path:
            yield unquote(url.path)


def _check_links(document, root, errors):
    link_errors = []
    for target in _links(document.read_text(encoding="utf-8"), link_errors):
        resolved = (document.parent / target).resolve()
        if not resolved.is_relative_to(root):
            errors.append(f"{document.relative_to(root)}: link outside repository: {target}")
        elif not resolved.exists():
            errors.append(f"{document.relative_to(root)}: missing reference: {target}")
    errors.extend(f"{document.relative_to(root)}: {error}" for error in link_errors)


def validate(repo_root):
    """Return concrete validation failures without changing files or using network."""
    root = Path(repo_root).resolve()
    errors = []
    folders = sorted(path for path in (root / "skills").glob("*") if path.is_dir())
    if not folders:
        return ["no skills found under skills/"]
    seen = set()
    catalogue = root / "SKILLS.md"
    indexed = set()
    if catalogue.is_file():
        indexed = {(catalogue.parent / link).resolve()
                   for link in _links(catalogue.read_text(encoding="utf-8"))}
        _check_links(catalogue, root, errors)
    else:
        errors.append("missing catalogue: SKILLS.md")
    for folder in folders:
        manifest = folder / "SKILL.md"
        label = manifest.relative_to(root)
        if not manifest.is_file():
            errors.append(f"{label}: missing manifest")
            continue
        document = manifest.read_text(encoding="utf-8")
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", document, re.DOTALL)
        if not match:
            errors.append(f"{label}: missing YAML frontmatter")
        else:
            try:
                metadata = yaml.load(match.group(1), Loader=UniqueKeyLoader)
                if not isinstance(metadata, dict):
                    errors.append(f"{label}: frontmatter must be a mapping")
                else:
                    name = metadata.get("name")
                    if not isinstance(name, str) or not NAME.fullmatch(name) or len(name) > 64:
                        errors.append(f"{label}: invalid skill name")
                    else:
                        if name != folder.name:
                            errors.append(f"{label}: name must match directory")
                        if name in seen:
                            errors.append(f"{label}: duplicate skill name: {name}")
                        seen.add(name)
                    description = metadata.get("description")
                    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
                        errors.append(f"{label}: description must be a nonempty string of at most 1024 characters")
            except (yaml.YAMLError, TypeError) as exc:
                errors.append(f"{label}: invalid YAML: {exc}")
        if manifest.resolve() not in indexed:
            errors.append(f"{label}: missing from catalogue SKILLS.md")
        link = root / ".agents" / "skills" / folder.name
        expected = f"../../skills/{folder.name}"
        if link.is_symlink():
            if link.readlink().as_posix() != expected or link.resolve() != folder.resolve():
                errors.append(f"{label}: incorrect discovery target: {link}")
        elif link.is_file():
            if link.read_text(encoding="utf-8").strip() != expected:
                errors.append(f"{label}: incorrect discovery link stub: {link}")
        else:
            errors.append(f"{label}: missing discovery link: .agents/skills/{folder.name}")
        for reference in sorted(folder.rglob("*.md")):
            _check_links(reference, root, errors)
    discovery = root / ".agents" / "skills"
    expected_names = {folder.name for folder in folders}
    for link in sorted(discovery.glob("*")):
        if link.name not in expected_names:
            errors.append(f"{link.relative_to(root)}: discovery entry has no canonical skill")
    return errors


def main(argv=None):
    """Print diagnostics; success proves structure, not agent task performance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    errors = validate(args.repo_root)
    for error in errors:
        print(error)
    if errors:
        return 1
    count = len(list((args.repo_root / "skills").glob("*/SKILL.md")))
    print(f"Validated {count} skills: metadata, catalogue, references and discovery targets.")
    stubs = [path for path in (args.repo_root / ".agents/skills").glob("*")
             if path.is_file() and not path.is_symlink()]
    if stubs:
        print("Git symlink stubs detected: use explicit loading from SKILLS.md; native discovery is unavailable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
