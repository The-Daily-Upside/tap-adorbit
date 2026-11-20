"""Tests for explicit stream schemas."""

import json

from tap_adorbit.schemas import STREAM_SCHEMAS
from tap_adorbit.streams import AdOrbitStream, MediaSlotItemsStream


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


def test_slot_channel_schemas_declare_join_keys():
    assert STREAM_SCHEMAS["ad_positions"]["properties"]["name"]["type"]
    slot = STREAM_SCHEMAS["media_slot_items"]["properties"]
    assert "channelId" in slot
    assert "order_modified" in slot


def test_slot_channel_id_is_stored_as_text():
    record = {"id": 3877, "channelId": 5.0, "gross": 12.5}
    MediaSlotItemsStream._stringify_scalars(record)
    assert record == {"id": "3877", "channelId": "5", "gross": "12.5"}


def test_product_category_catalog_stringifies_ids_and_ignores_start_date():
    from tap_adorbit.streams import ProductCategoriesStream
    from tap_adorbit.tap import TapAdOrbit

    tap = TapAdOrbit(
        config={
            "instance": "stage",
            "public_key": "pub",
            "private_key": "priv",
            "start_date": "2020-01-01 00:00:00",
        },
        validate_config=False,
        parse_env_config=False,
    )
    stream = ProductCategoriesStream(tap)
    seen = {}

    def _paginated(endpoint_key, limit=100, changed_since=None, records_key=None):
        seen["endpoint_key"] = endpoint_key
        seen["changed_since"] = changed_since
        yield {
            "id": 37,
            "name": "Newsletter",
            "description": None,
            "type": "slot",
        }

    stream._client.get_paginated = _paginated
    rows = list(stream.get_records(None))
    assert seen == {"endpoint_key": "product-categories", "changed_since": None}
    assert rows == [
        {
            "id": "37",
            "name": "Newsletter",
            "description": None,
            "type": "slot",
            "is_deleted": False,
            "_raw": json.dumps(
                {
                    "id": 37,
                    "name": "Newsletter",
                    "description": None,
                    "type": "slot",
                }
            ),
        }
    ]


def test_service_sale_ids_are_stringified():
    order = {
        "serviceSales": [
            {"id": 3877, "serviceName": "Advisor Upside - Weekday"},
            {"id": None},
            "not-a-sale",
        ]
    }
    assert MediaSlotItemsStream._service_sale_ids(order) == ["3877"]


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
