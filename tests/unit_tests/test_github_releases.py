"""Tests for authenticated GitHub release metadata requests."""

import json

from utils import github_releases


class JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_read_json_uses_ci_github_token(monkeypatch):
    observed = {}

    def fake_urlopen(request):
        observed["request"] = request
        return JsonResponse({"tag_name": "v1"})

    monkeypatch.setenv("ALPHAGSM_GITHUB_TOKEN", "ci-token")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(github_releases.urllib.request, "urlopen", fake_urlopen)

    result = github_releases.read_json(
        "https://api.github.com/repos/example/project/releases/latest"
    )

    assert result == {"tag_name": "v1"}
    assert observed["request"].get_header("Authorization") == "Bearer ci-token"
    assert observed["request"].get_header("User-agent") == github_releases.HTTP_USER_AGENT


def test_read_json_omits_authorization_without_token(monkeypatch):
    observed = {}

    def fake_urlopen(request):
        observed["request"] = request
        return JsonResponse({})

    monkeypatch.delenv("ALPHAGSM_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(github_releases.urllib.request, "urlopen", fake_urlopen)

    github_releases.read_json(
        "https://api.github.com/repos/example/project/releases/latest"
    )

    assert observed["request"].get_header("Authorization") is None


def test_subprocess_env_exposes_alphagsm_token_as_github_token(monkeypatch):
    monkeypatch.setenv("ALPHAGSM_GITHUB_TOKEN", "ci-token")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    env = github_releases.authenticated_subprocess_env()

    assert env["GITHUB_TOKEN"] == "ci-token"


def test_subprocess_env_preserves_explicit_github_token(monkeypatch):
    monkeypatch.setenv("ALPHAGSM_GITHUB_TOKEN", "ci-token")
    monkeypatch.setenv("GITHUB_TOKEN", "explicit-token")

    env = github_releases.authenticated_subprocess_env()

    assert env["GITHUB_TOKEN"] == "explicit-token"
