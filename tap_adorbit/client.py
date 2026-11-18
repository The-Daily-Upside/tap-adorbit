"""HTTP client for the Ad Orbit API."""

import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# One empty 500 is Ad Orbit's response for a service sale that is not a slot.
# Five in a row, with no other slot response between them, is an outage.
_EMPTY_500_STREAK_LIMIT = 5
_NOT_A_SLOT_500 = object()


class AdOrbitClient:
    """Client for Ad Orbit REST API with HMAC-SHA512 authentication."""

    def __init__(
        self,
        instance: str,
        public_key: str,
        private_key: str,
        api_scheme: str = "https",
    ):
        instance = instance.strip().removesuffix(".adorbit.com")
        if instance.endswith(".api.adorbit.com"):
            instance = instance.removesuffix(".api.adorbit.com")
        self.base_url = f"{api_scheme}://{instance}.api.adorbit.com/"
        self.public_key = public_key
        self.private_key = private_key
        self._root: Optional[Dict[str, Any]] = None
        self._empty_500_streak = 0

    def _sign(self, method: str, uri: str) -> str:
        """Generate the base64-encoded HMAC-SHA512 signature for a request."""
        message = f"{method.upper()}\n{uri}"
        digest = hmac.new(
            self.private_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()
        return base64.b64encode(digest.encode("utf-8")).decode("utf-8")

    def _auth_header(self, method: str, uri: str) -> str:
        signature = self._sign(method, uri)
        return f"ADORBIT {self.public_key}:{signature}"

    def request(
        self,
        method: str,
        uri: str,
        extra_headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        missing_ok_statuses: Optional[set] = None,
        empty_500_as_missing: bool = False,
    ) -> Any:
        """Make an authenticated request and return the JSON response."""
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            signed_uri = f"{uri}?{query}" if "?" not in uri else f"{uri}&{query}"
        else:
            signed_uri = uri

        headers = {
            "Accept": "application/json",
            "Authorization": self._auth_header(method, signed_uri),
        }
        if extra_headers:
            headers.update(extra_headers)

        # 429 is Ad Orbit throttling. 502/503/504 are the gateway blips that abort
        # a long orders page (HTML "Bad Gateway") after rows have already loaded.
        retryable = {429, 502, 503, 504}
        max_retries = 8
        backoff = 5
        for attempt in range(max_retries):
            response = requests.request(method, signed_uri, headers=headers, timeout=120)
            if response.status_code in retryable and attempt < max_retries - 1:
                logger.warning(
                    "Ad Orbit API %s for %s (attempt %s), backing off %s seconds.",
                    response.status_code,
                    signed_uri,
                    attempt + 1,
                    backoff,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)
                continue
            if missing_ok_statuses and response.status_code in missing_ok_statuses:
                return None
            body = (response.text or "").strip()
            if (
                empty_500_as_missing
                and response.status_code == 500
                and not body
            ):
                self._empty_500_streak += 1
                if self._empty_500_streak >= _EMPTY_500_STREAK_LIMIT:
                    logger.error(
                        "Ad Orbit returned %s empty 500s in a row for %s; failing the sync.",
                        self._empty_500_streak,
                        signed_uri,
                    )
                    response.raise_for_status()
                logger.warning(
                    "Ad Orbit returned an empty 500 for %s (%s in a row); "
                    "treating it as not a slot item.",
                    signed_uri,
                    self._empty_500_streak,
                )
                return _NOT_A_SLOT_500
            if response.status_code >= 400:
                logger.error(
                    "Ad Orbit API error %s for %s: %s",
                    response.status_code,
                    signed_uri,
                    response.text,
                )
            response.raise_for_status()
            return response.json()

        raise RuntimeError(f"Max retries exceeded for {signed_uri}.")

    def get_optional(self, uri: str) -> Optional[Dict[str, Any]]:
        """GET one record. A confirmed miss returns None.

        Slot lookups use the service-sale id. A line that is not a slot returns
        HTTP 404, ``{"error": "Item not found."}``, or an empty HTTP 500.
        HTTP 405, a 500 with a body, and five empty 500s in a row propagate.
        A successful order-list page does not clear that streak.
        """
        payload = self.request(
            "GET",
            uri,
            missing_ok_statuses={404},
            empty_500_as_missing=True,
        )
        if payload is _NOT_A_SLOT_500:
            return None
        # A 404, a not-found body, or a real slot breaks the empty-500 streak.
        # Order-list pages must not: they succeed while this endpoint is down.
        self._empty_500_streak = 0
        if not isinstance(payload, dict) or "id" not in payload:
            return None
        return payload

    def get_root(self) -> Dict[str, Any]:
        """Fetch and cache the root endpoint map (HATEOAS links)."""
        if self._root is None:
            self._root = self.request("GET", self.base_url)
        return self._root

    def get_endpoint_url(self, endpoint_key: str) -> str:
        """Resolve a resource URL from the root endpoint map."""
        root = self.get_root()
        if endpoint_key not in root:
            raise KeyError(
                f"Endpoint '{endpoint_key}' not found in Ad Orbit root response. "
                f"Available keys: {sorted(root.keys())}"
            )
        return root[endpoint_key]

    @staticmethod
    def _pagination_params(
        limit: int,
        offset: int,
        changed_since: Optional[str] = None,
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Build pagination headers and query params for list endpoints.

        The official API docs describe ``changedsince`` as a query parameter on
        list endpoints. Live instances also honor ``X-OPT-*`` headers, so we
        send both. Offset is a 0-based page index (not a row offset): with
        limit=10, offset=2 returns records 21-30.
        """
        headers = {
            "X-OPT-LIMIT": str(limit),
            "X-OPT-OFFSET": str(offset),
        }
        params: Dict[str, str] = {}
        if changed_since:
            headers["X-OPT-CHANGEDSINCE"] = changed_since
            params["changedsince"] = changed_since
        return headers, params

    def get_paginated(
        self,
        endpoint_key: str,
        limit: int = 100,
        changed_since: Optional[str] = None,
        records_key: Optional[str] = None,
    ):
        """Yield all records from a list endpoint, handling offset pagination."""
        url = self.get_endpoint_url(endpoint_key)
        offset = 0

        while True:
            extra_headers, params = self._pagination_params(limit, offset, changed_since)
            data = self.request("GET", url, extra_headers=extra_headers, params=params or None)
            records = self._extract_records(data, endpoint_key, records_key)
            if not records:
                break

            yield from records

            if len(records) < limit:
                break
            offset += 1
            time.sleep(0.25)

    @staticmethod
    def _extract_records(
        data: Any,
        endpoint_key: str,
        records_key: Optional[str] = None,
    ) -> list:
        """Extract a list of records from an API response."""
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []

        keys_to_try = []
        if records_key:
            keys_to_try.append(records_key)

        # Try endpoint name, singular form, then known Ad Orbit aliases.
        singular = endpoint_key.rstrip("s") if endpoint_key.endswith("s") else endpoint_key
        keys_to_try.extend(
            [
                endpoint_key,
                singular,
                "assets",
                "data",
                "items",
                "results",
                "records",
            ]
        )

        seen = set()
        for key in keys_to_try:
            if key in seen:
                continue
            seen.add(key)
            if key in data and isinstance(data[key], list):
                return data[key]

        # Last resort: first list-of-objects value in the payload.
        for value in data.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value

        return []
