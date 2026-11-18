"""Unit tests for Ad Orbit response parsing."""

import pytest
import requests

from tap_adorbit.client import AdOrbitClient


def test_extract_records_uses_endpoint_collection_key():
    payload = {"companies": [{"id": "1"}], "links": {}}
    assert AdOrbitClient._extract_records(payload, "companies") == [{"id": "1"}]


def test_extract_records_uses_assets_override():
    payload = {"assets": [{"id": "1", "name": "No Plan"}], "links": {}}
    assert AdOrbitClient._extract_records(payload, "subscriptionplans", "assets") == [
        {"id": "1", "name": "No Plan"}
    ]


def test_extract_records_returns_empty_list_for_empty_collection():
    payload = {"subscribers": [], "links": {}}
    assert AdOrbitClient._extract_records(payload, "subscribers") == []


def test_pagination_params_include_changedsince_query_and_header():
    headers, params = AdOrbitClient._pagination_params(50, 0, "2026-01-01 00:00:00")
    assert headers["X-OPT-LIMIT"] == "50"
    assert headers["X-OPT-OFFSET"] == "0"
    assert headers["X-OPT-CHANGEDSINCE"] == "2026-01-01 00:00:00"
    assert params["changedsince"] == "2026-01-01 00:00:00"


def test_pagination_params_omit_changedsince_when_not_set():
    headers, params = AdOrbitClient._pagination_params(100, 2, None)
    assert headers["X-OPT-OFFSET"] == "2"
    assert "X-OPT-CHANGEDSINCE" not in headers
    assert params == {}


def test_get_optional_treats_404_as_missing(monkeypatch):
    class _Response:
        status_code = 404
        text = ""

        def raise_for_status(self):
            raise AssertionError("404 should be treated as a missing slot item")

        def json(self):
            raise AssertionError("404 body is not parsed")

    monkeypatch.setattr(
        "tap_adorbit.client.requests.request",
        lambda *args, **kwargs: _Response(),
    )
    client = AdOrbitClient("stage", "pub", "priv")
    assert client.get_optional("https://stage.api.adorbit.com/media-slot-item/1") is None


@pytest.mark.parametrize("status_code", [405, 500])
def test_get_optional_raises_on_unexpected_http_error(monkeypatch, status_code):
    class _Response:
        def __init__(self):
            self.status_code = status_code
            self.text = "nope"

        def raise_for_status(self):
            raise requests.HTTPError(f"{self.status_code}")

        def json(self):
            raise AssertionError("error body should not be parsed as a record")

    monkeypatch.setattr(
        "tap_adorbit.client.requests.request",
        lambda *args, **kwargs: _Response(),
    )
    client = AdOrbitClient("stage", "pub", "priv")
    with pytest.raises(requests.HTTPError):
        client.get_optional("https://stage.api.adorbit.com/media-slot-item/1")


def test_get_optional_ignores_not_found_payload(monkeypatch):
    client = AdOrbitClient("stage", "pub", "priv")
    monkeypatch.setattr(client, "request", lambda *args, **kwargs: {"error": "Item not found."})
    assert client.get_optional("https://stage.api.adorbit.com/media-slot-item/1") is None
    monkeypatch.setattr(
        client,
        "request",
        lambda *args, **kwargs: {"id": 3877, "channelId": 5},
    )
    assert client.get_optional("https://stage.api.adorbit.com/media-slot-item/3877")["channelId"] == 5


def test_request_retries_gateway_errors_then_returns_json(monkeypatch):
    calls = {"n": 0}

    class _Response:
        def __init__(self, status_code, payload=None):
            self.status_code = status_code
            self.text = "bad gateway" if status_code >= 400 else ""
            self._payload = payload or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise AssertionError(f"should have retried status {self.status_code}")

        def json(self):
            return self._payload

    def _request(method, uri, headers, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            return _Response(502)
        return _Response(200, {"ok": True})

    monkeypatch.setattr("tap_adorbit.client.requests.request", _request)
    monkeypatch.setattr("tap_adorbit.client.time.sleep", lambda _seconds: None)

    client = AdOrbitClient("stage", "pub", "priv")
    assert client.request("GET", "https://stage.api.adorbit.com/orders") == {"ok": True}
    assert calls["n"] == 3


def test_normalize_record_backfills_replication_timestamps():
    from tap_adorbit.streams import AdOrbitStream

    record = {
        "id": "1",
        "contact_created_date": "2026-01-01 00:00:00",
        "contact_updated_date": None,
    }
    normalized = AdOrbitStream._normalize_record(record, "contacts")
    assert normalized["contact_updated_date"] == "2026-01-01 00:00:00"
