"""Unit tests for Ad Orbit response parsing."""

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


def test_normalize_record_backfills_replication_timestamps():
    from tap_adorbit.streams import AdOrbitStream

    record = {
        "id": "1",
        "contact_created_date": "2026-01-01 00:00:00",
        "contact_updated_date": None,
    }
    normalized = AdOrbitStream._normalize_record(record, "contacts")
    assert normalized["contact_updated_date"] == "2026-01-01 00:00:00"
