"""Release publication is limited to successful trusted tag pushes."""
from pathlib import Path


def test_manual_tag_dispatch_cannot_sign_or_publish():
    text = Path('.github/workflows/release.yml').read_text()
    assert "release: ${{ github.event_name == 'push' && startsWith(github.ref, 'refs/tags/') }}" in text
    publish = text.split('  publish:', 1)[1]
    assert "if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')" in publish


def test_binary_evidence_uploads_only_verifier_owned_outputs():
    text = Path('.github/workflows/binary.yml').read_text()
    evidence = text.split('      - name: Retain acceptance diagnostics', 1)[1].split('      - name:', 1)[0]
    assert 'binary-evidence/evidence/' in evidence
    assert 'binary-docker-evidence/evidence/' in evidence
    assert '**' not in evidence
    assert 'include-hidden-files: true' not in evidence
    assert '*.secrets.json' not in evidence
    assert 'path: binary-evidence/' not in evidence
