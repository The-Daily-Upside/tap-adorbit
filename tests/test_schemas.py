"""Tests for explicit stream schemas."""

import json

from tap_adorbit.schemas import STREAM_SCHEMAS
from tap_adorbit.streams import AdOrbitStream


def test_companies_schema_includes_business_fields():
    properties = STREAM_SCHEMAS["companies"]["properties"]
    assert "name" in properties
    assert "website" in properties
    assert "primary_contact" in properties
    assert "_raw" in properties


def test_normalize_record_serializes_nested_values():
    record = {
        "id": "1",
        "name": "Example Co",
        "links": {"self": "https://example.com/companies/1"},
        "primary_contact": {"name": "Jane Doe"},
    }
    normalized = AdOrbitStream._normalize_record(record, "companies")
    assert normalized["name"] == "Example Co"
    assert json.loads(normalized["links"]) == {"self": "https://example.com/companies/1"}
    assert json.loads(normalized["primary_contact"]) == {"name": "Jane Doe"}
    raw = json.loads(normalized["_raw"])
    assert raw["links"] == {"self": "https://example.com/companies/1"}
    assert raw["primary_contact"] == {"name": "Jane Doe"}


def test_unknown_fields_are_kept_in_raw_but_not_emitted():
    record = {
        "id": "1",
        "name": "Example Co",
        "futureField": "new value",
    }
    normalized = AdOrbitStream._normalize_record(record, "companies")
    raw = json.loads(normalized["_raw"])
    assert raw["futureField"] == "new value"

    allowed = set(STREAM_SCHEMAS["companies"]["properties"])
    emitted = {key: normalized[key] for key in allowed if key in normalized}
    assert "futureField" not in emitted
    assert emitted["name"] == "Example Co"
