"""Ad Orbit stream definitions."""

import json
from typing import Any, Dict, Iterable, Optional

from singer_sdk.streams import Stream

from tap_adorbit.client import AdOrbitClient
from tap_adorbit.schemas import STREAM_SCHEMAS

# Ad Orbit soft-delete signals vary by resource. We always sync deleted rows so
# Postgres stays accurate when something is deactivated, and expose is_deleted for
# filtered reporting views (adorbit.v_*).
_IS_ACTIVE_STRING = {"1", "true", "yes"}


class AdOrbitStream(Stream):
    """Base stream for Ad Orbit list endpoints."""

    endpoint_key: str = ""
    records_key: Optional[str] = None
    primary_keys = ["id"]
    replication_key: Optional[str] = None

    def __init__(self, tap):
        super().__init__(tap)
        self._client = AdOrbitClient(
            instance=tap.config["instance"],
            public_key=tap.config["public_key"],
            private_key=tap.config["private_key"],
            api_scheme=tap.config.get("api_scheme", "https"),
        )

    @property
    def page_size(self) -> int:
        return int(self.config.get("page_size") or 100)

    def get_records(self, context: Optional[dict]) -> Iterable[Dict[str, Any]]:
        changed_since = self.config.get("start_date")
        if self.replication_key:
            bookmark = self.get_starting_replication_key_value(context)
            if bookmark:
                changed_since = bookmark

        allowed_keys = set(self.schema["properties"].keys())
        for record in self._client.get_paginated(
            self.endpoint_key,
            limit=self.page_size,
            changed_since=changed_since,
            records_key=self.records_key,
        ):
            normalized = self._normalize_record(record, self.name)
            yield {key: normalized[key] for key in allowed_keys if key in normalized}

    @staticmethod
    def _compute_is_deleted(stream_name: str, record: Dict[str, Any]) -> bool:
        if stream_name in {"companies", "contacts"}:
            return record.get("active") is not True

        if stream_name == "activities":
            return str(record.get("deleted", "0")) == "1"

        if stream_name in {"publications", "subscriptionplans", "subscribers"}:
            active = record.get("active")
            if active is None:
                return False
            if isinstance(active, bool):
                return not active
            return str(active).lower() not in _IS_ACTIVE_STRING

        if stream_name == "subscriptions":
            return str(record.get("status", "")) == "3"

        return False

    @staticmethod
    def _normalize_record(record: Dict[str, Any], stream_name: str) -> Dict[str, Any]:
        """Ensure records have a stable primary key and replication timestamps."""
        raw_record = json.dumps(record)
        is_deleted = AdOrbitStream._compute_is_deleted(stream_name, record)

        if "id" not in record:
            for key in ("cid", "company_id", "contact_id", "order_id"):
                if key in record:
                    record["id"] = record[key]
                    break

        # Ad Orbit often leaves updated timestamps null; fall back to created dates
        # so Singer incremental bookmarks do not warn on every record.
        replication_fallbacks = {
            "company_updated_date": "company_created_date",
            "contact_updated_date": "contact_created_date",
            "order_modified": "createDate",
            "modified": "created",
        }
        for replication_key, fallback_key in replication_fallbacks.items():
            if not record.get(replication_key) and record.get(fallback_key):
                record[replication_key] = record[fallback_key]

        for key, value in list(record.items()):
            if isinstance(value, (dict, list)):
                record[key] = json.dumps(value)

        record["is_deleted"] = is_deleted
        record["_raw"] = raw_record
        return record


class CompaniesStream(AdOrbitStream):
    name = "companies"
    endpoint_key = "companies"
    replication_key = "company_updated_date"
    schema = STREAM_SCHEMAS["companies"]


class ContactsStream(AdOrbitStream):
    name = "contacts"
    endpoint_key = "contacts"
    replication_key = "contact_updated_date"
    schema = STREAM_SCHEMAS["contacts"]


class ActivitiesStream(AdOrbitStream):
    name = "activities"
    endpoint_key = "activities"
    replication_key = "modified"
    schema = STREAM_SCHEMAS["activities"]


class OrdersStream(AdOrbitStream):
    name = "orders"
    endpoint_key = "orders"
    replication_key = "order_modified"
    schema = STREAM_SCHEMAS["orders"]


class SubscribersStream(AdOrbitStream):
    name = "subscribers"
    endpoint_key = "subscribers"
    schema = STREAM_SCHEMAS["subscribers"]


class SubscriptionsStream(AdOrbitStream):
    name = "subscriptions"
    endpoint_key = "subscriptions"
    schema = STREAM_SCHEMAS["subscriptions"]


class SubscriptionPlansStream(AdOrbitStream):
    name = "subscriptionplans"
    endpoint_key = "subscriptionplans"
    records_key = "assets"
    replication_key = "expiration_date"
    schema = STREAM_SCHEMAS["subscriptionplans"]


class PublicationsStream(AdOrbitStream):
    name = "publications"
    endpoint_key = "publications"
    schema = STREAM_SCHEMAS["publications"]


class EditorialsStream(AdOrbitStream):
    name = "editorials"
    endpoint_key = "editorials"
    schema = STREAM_SCHEMAS["editorials"]


class VendorsStream(AdOrbitStream):
    name = "vendors"
    endpoint_key = "vendors"
    schema = STREAM_SCHEMAS["vendors"]


class CompanyAssetsStream(AdOrbitStream):
    name = "companyassets"
    endpoint_key = "companyassets"
    records_key = "assets"
    schema = STREAM_SCHEMAS["companyassets"]
