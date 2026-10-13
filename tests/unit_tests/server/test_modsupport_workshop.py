"""Valve Workshop metadata filters and collection expansion tests."""

import io
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs

import pytest

from server.modsupport.errors import ModSupportError


def detail(item_id, app_id=730, file_type=0, result=1):
    return {"publishedfileid": str(item_id), "consumer_app_id": app_id,
            "file_type": file_type, "result": result}


def fake_api(monkeypatch, details, collections=None):
    from server.modsupport import workshop
    calls = []

    def respond(request, timeout):
        assert timeout == 30
        params = parse_qs(request.data.decode())
        calls.append((request.full_url, params))
        ids = [params[f"publishedfileids[{index}]"][0]
               for index in range(int(params.get("itemcount", params.get("collectioncount"))[0]))]
        if "GetPublishedFileDetails" in request.full_url:
            records = [details.get(item_id, detail(item_id, result=9)) for item_id in ids]
            payload = {"response": {"publishedfiledetails": records}}
        else:
            payload = {"response": {"collectiondetails": [
                {"publishedfileid": item_id, "result": 1 if item_id in (collections or {}) else 9, "children": [
                    {"publishedfileid": str(child)} for child in (collections or {}).get(item_id, [])
                ]} for item_id in ids
            ]}}
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(workshop, "urlopen", respond)
    return workshop, calls


def test_item_must_belong_to_expected_game(monkeypatch):
    provider, _ = fake_api(monkeypatch, {"10": detail(10)})
    assert provider.resolve_workshop_item("10", 730)["workshop_id"] == "10"
    with pytest.raises(ModSupportError, match="belongs to.*730.*440"):
        provider.resolve_workshop_item("10", 440)


def test_legacy_item_metadata_without_file_type_is_supported(monkeypatch):
    record = detail(10, app_id=550)
    record.pop("file_type")
    record.update(filename="addons/example.vpk", hcontent_file="123", file_url="https://cdn.steamusercontent.com/ugc/example")
    provider, _ = fake_api(monkeypatch, {"10": record})
    assert provider.resolve_workshop_item("10", 550)["workshop_id"] == "10"


def test_legacy_collection_metadata_without_file_type_is_supported(monkeypatch):
    record = detail(1, app_id=550, file_type=2)
    record.pop("file_type")
    record.update(filename="", hcontent_file="0", file_url="")
    provider, _ = fake_api(monkeypatch, {"1": record, "10": detail(10, app_id=550)}, {"1": [10]})
    assert provider.resolve_workshop_collection("1", 550) == ["10"]


@pytest.mark.parametrize('filename', ['steamworkshop/collection/1_collection_branding.jpg', ''])
def test_legacy_collection_branding_image_is_not_a_downloadable_mod(monkeypatch, filename):
    record = detail(1, app_id=550, file_type=None)
    record.update(filename=filename,
                  file_url='https://images.steamusercontent.com/ugc/image', hcontent_file='900985983942213642')
    provider, _calls = fake_api(monkeypatch, {'1': record, '10': detail(10, app_id=550)}, {'1': [10]})
    assert provider.resolve_workshop_collection('1', 550) == ['10']
    with pytest.raises(ModSupportError, match='collection'):
        provider.resolve_workshop_item('1', 550)


def test_batch_item_validation_shares_request_budget(monkeypatch):
    ids = [str(index) for index in range(1, 251)]
    provider, calls = fake_api(monkeypatch, {identifier: detail(identifier) for identifier in ids})
    assert [entry["workshop_id"] for entry in provider.resolve_workshop_items(ids, 730)] == ids
    assert len(calls) == 3
    monkeypatch.setattr(provider, "MAX_WORKSHOP_REQUESTS", 2)
    with pytest.raises(ModSupportError, match="limit"):
        provider.resolve_workshop_items(ids, 730)


@pytest.mark.parametrize("record", [detail(10, result=9), detail(10, file_type=2),
                                   {"publishedfileid": "10", "result": 1, "file_type": 0},
                                   detail(11), detail(10, app_id=0)])
def test_unavailable_or_invalid_item_metadata_rejected(monkeypatch, record):
    provider, _ = fake_api(monkeypatch, {"10": record})
    with pytest.raises(ModSupportError):
        provider.resolve_workshop_item("10", 730)


def test_nested_collection_preserves_order_and_deduplicates(monkeypatch):
    records = {"1": detail(1, file_type=2), "2": detail(2, file_type=2),
               "10": detail(10), "11": detail(11), "12": detail(12)}
    provider, _ = fake_api(monkeypatch, records, {"1": [10, 2, 10, 12], "2": [11, 10]})
    assert provider.resolve_workshop_collection("1", 730) == ["10", "11", "12"]


@pytest.mark.parametrize("wrong_id", ["1", "2", "11"])
def test_collection_checks_root_nested_collection_and_every_child(monkeypatch, wrong_id):
    records = {"1": detail(1, file_type=2), "2": detail(2, file_type=2),
               "10": detail(10), "11": detail(11)}
    records[wrong_id]["consumer_app_id"] = 440
    provider, _ = fake_api(monkeypatch, records, {"1": [10, 2], "2": [11]})
    with pytest.raises(ModSupportError, match="belongs to.*440.*730"):
        provider.resolve_workshop_collection("1", 730)


def test_collection_cycles_rejected(monkeypatch):
    provider, _ = fake_api(monkeypatch, {"1": detail(1, file_type=2),
                                       "2": detail(2, file_type=2)}, {"1": [2], "2": [1]})
    with pytest.raises(ModSupportError, match="cycle"):
        provider.resolve_workshop_collection("1", 730)


def test_collection_with_unavailable_child_fails_instead_of_partial_import(monkeypatch):
    provider, _ = fake_api(monkeypatch, {"1": detail(1, file_type=2), "10": detail(10)},
                           {"1": [10, 11]})
    with pytest.raises(ModSupportError, match="unavailable"):
        provider.resolve_workshop_collection("1", 730)


def test_empty_collection_rejected(monkeypatch):
    provider, _ = fake_api(monkeypatch, {"1": detail(1, file_type=2)}, {"1": []})
    with pytest.raises(ModSupportError, match="empty"):
        provider.resolve_workshop_collection("1", 730)


def test_item_is_not_a_collection(monkeypatch):
    provider, _ = fake_api(monkeypatch, {"10": detail(10)})
    with pytest.raises(ModSupportError, match="collection"):
        provider.resolve_workshop_collection("10", 730)


def test_collection_size_and_request_limits(monkeypatch):
    provider, _ = fake_api(monkeypatch, {"1": detail(1, file_type=2), "10": detail(10),
                                       "11": detail(11)}, {"1": [10, 11]})
    monkeypatch.setattr(provider, "MAX_WORKSHOP_NODES", 2)
    with pytest.raises(ModSupportError, match="limit"):
        provider.resolve_workshop_collection("1", 730)
    monkeypatch.setattr(provider, "MAX_WORKSHOP_NODES", 100)
    monkeypatch.setattr(provider, "MAX_WORKSHOP_REQUESTS", 1)
    with pytest.raises(ModSupportError, match="limit"):
        provider.resolve_workshop_collection("1", 730)


@pytest.mark.parametrize("identifier", ["0", "-1", "12\n", "١٢", "1 +quit", str(2**64)])
def test_invalid_ids_rejected_before_api(monkeypatch, identifier):
    provider, calls = fake_api(monkeypatch, {})
    with pytest.raises(ModSupportError, match="numeric workshop id"):
        provider.resolve_workshop_item(identifier, 730)
    assert calls == []


@pytest.mark.parametrize("payload", [b"bad JSON", b"{}", b'{"response":{"publishedfiledetails":null}}'])
def test_malformed_api_response_rejected(monkeypatch, payload):
    provider, _ = fake_api(monkeypatch, {})
    monkeypatch.setattr(provider, "urlopen", lambda *a, **kw: io.BytesIO(payload))
    with pytest.raises(ModSupportError, match="Steam Workshop"):
        provider.resolve_workshop_item("10", 730)


def test_transient_api_error_retried_but_access_error_not_retried(monkeypatch):
    provider, _ = fake_api(monkeypatch, {})
    attempts = []

    def unavailable(request, timeout):
        attempts.append(request)
        raise HTTPError(request.full_url, 503, "Unavailable", {}, None)

    monkeypatch.setattr(provider, "urlopen", unavailable)
    monkeypatch.setattr(provider.time, "sleep", lambda _: None)
    with pytest.raises(ModSupportError, match="Steam Workshop"):
        provider.resolve_workshop_item("10", 730)
    assert len(attempts) == 3
    attempts.clear()

    def denied(request, timeout):
        attempts.append(request)
        raise HTTPError(request.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(provider, "urlopen", denied)
    with pytest.raises(ModSupportError):
        provider.resolve_workshop_item("10", 730)
    assert len(attempts) == 1


@pytest.mark.parametrize('identifier', [
    '10', 10,
    'https://steamcommunity.com/sharedfiles/filedetails/?id=10',
    'http://www.steamcommunity.com/sharedfiles/filedetails?id=00010&searchtext=server',
    'https://steamcommunity.com/workshop/filedetails/?id=10#comments',
])
def test_item_ids_and_workshop_urls_are_interchangeable(monkeypatch, identifier):
    provider, calls = fake_api(monkeypatch, {'10': detail(10)})
    assert provider.resolve_workshop_item(identifier, 730)['workshop_id'] == '10'
    assert calls[0][1]['publishedfileids[0]'] == ['10']


def test_collection_url_expands_with_game_filter(monkeypatch):
    provider, _ = fake_api(monkeypatch, {'1': detail(1, file_type=2), '10': detail(10)}, {'1': ['10']})
    assert provider.resolve_workshop_collection('https://steamcommunity.com/sharedfiles/filedetails/?id=1', 730) == ['10']


@pytest.mark.parametrize('identifier', [
    'https://steamcommunity.com.evil.example/sharedfiles/filedetails/?id=10',
    'https://evil.example/?id=10',
    'https://steamcommunity.com@evil.example/sharedfiles/filedetails/?id=10',
    'https://user@steamcommunity.com/sharedfiles/filedetails/?id=10',
    'https://steamcommunity.com:1234/sharedfiles/filedetails/?id=10',
    'https://steamcommunity.com/sharedfiles/filedetails/?id=10&id=11',
    'https://steamcommunity.com/sharedfiles/filedetails/?id=',
    'https://steamcommunity.com/app/10',
    'https://steamcommunity.com/sharedfiles/filedetails/?id=18446744073709551616',
    'https://steamcommunity.com/sharedfiles/filedetails/?id=0',
    'https://steamcommunity.com/sharedfiles/filedetails/?id=abc',
])
def test_invalid_workshop_urls_fail_before_network(monkeypatch, identifier):
    provider, calls = fake_api(monkeypatch, {})
    with pytest.raises(ModSupportError):
        provider.resolve_workshop_item(identifier, 730)
    assert calls == []
