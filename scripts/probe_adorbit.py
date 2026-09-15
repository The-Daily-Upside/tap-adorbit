#!/usr/bin/env python3
"""Probe the Ad Orbit API and save raw responses for schema development.

Usage:
  cp config.example.json config.json   # fill in real keys
  python scripts/probe_adorbit.py
  python scripts/probe_adorbit.py --endpoints companies contacts
  python scripts/probe_adorbit.py --limit 10 --output sample_responses
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Allow running from repo root without installing.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tap_adorbit.client import AdOrbitClient

RECORDS_KEY_OVERRIDES = {
    "subscriptionplans": "assets",
    "companyassets": "assets",
}

DEFAULT_ENDPOINTS = [
    "companies",
    "contacts",
    "activities",
    "orders",
    "subscribers",
    "subscriptions",
    "subscriptionplans",
    "publications",
    "editorials",
    "vendors",
    "companyassets",
]


def load_config(path: Path) -> dict:
    with path.open() as handle:
        return json.load(handle)


def summarize_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        if not value:
            return "array<empty>"
        inner = summarize_value(value[0])
        return f"array<{inner}>"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def summarize_records(records: list[dict]) -> dict[str, str]:
    field_types: dict[str, set[str]] = {}
    for record in records:
        for key, value in record.items():
            field_types.setdefault(key, set()).add(summarize_value(value))
    return {key: "|".join(sorted(types)) for key, types in sorted(field_types.items())}


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Ad Orbit API responses.")
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to tap config JSON (default: config.json)",
    )
    parser.add_argument(
        "--output",
        default="sample_responses",
        help="Directory to write JSON response files (default: sample_responses)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="X-OPT-LIMIT for list endpoints (default: 5)",
    )
    parser.add_argument(
        "--endpoints",
        nargs="*",
        help="Specific root endpoint keys to probe (default: all list streams)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        print("Copy config.example.json to config.json and add your API keys.", file=sys.stderr)
        return 1

    config = load_config(config_path)
    client = AdOrbitClient(
        instance=config["instance"],
        public_key=config["public_key"],
        private_key=config["private_key"],
        api_scheme=config.get("api_scheme", "https"),
    )

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Base URL: {client.base_url}")
    print(f"Writing responses to: {output_dir.resolve()}\n")

    root = client.get_root()
    root_path = output_dir / "root.json"
    root_path.write_text(json.dumps(root, indent=2, sort_keys=True))
    print(f"saved root.json ({len(root)} keys)")

    endpoints = args.endpoints or DEFAULT_ENDPOINTS
    summary: dict[str, Any] = {"base_url": client.base_url, "endpoints": {}}

    for endpoint_key in endpoints:
        print(f"\n--- {endpoint_key} ---")
        try:
            url = client.get_endpoint_url(endpoint_key)
        except KeyError as exc:
            print(f"SKIP: {exc}")
            summary["endpoints"][endpoint_key] = {"status": "missing_from_root"}
            continue

        try:
            payload = client.request(
                "GET",
                url,
                extra_headers={
                    "X-OPT-LIMIT": str(args.limit),
                    "X-OPT-OFFSET": "0",
                },
            )
        except Exception as exc:
            print(f"ERROR: {exc}")
            summary["endpoints"][endpoint_key] = {"status": "request_failed", "error": str(exc)}
            continue

        out_file = output_dir / f"{endpoint_key}.json"
        out_file.write_text(json.dumps(payload, indent=2, sort_keys=True))
        records = client._extract_records(
            payload,
            endpoint_key,
            RECORDS_KEY_OVERRIDES.get(endpoint_key),
        )

        top_level_type = type(payload).__name__
        top_level_keys = list(payload.keys()) if isinstance(payload, dict) else []
        field_summary = summarize_records(records) if records else {}

        print(f"url: {url}")
        print(f"saved: {out_file.name}")
        print(f"top-level: {top_level_type}", end="")
        if top_level_keys:
            print(f" keys={top_level_keys}")
        else:
            print()
        print(f"extracted records: {len(records)}")
        if records:
            print(f"sample record keys: {list(records[0].keys())}")
            print("field types:")
            for field, types in field_summary.items():
                print(f"  {field}: {types}")

        summary["endpoints"][endpoint_key] = {
            "status": "ok",
            "url": url,
            "top_level_type": top_level_type,
            "top_level_keys": top_level_keys,
            "record_count": len(records),
            "fields": field_summary,
            "candidate_primary_keys": [
                key
                for key in ("id", "cid", "company_id", "contact_id", "order_id")
                if key in field_summary
            ],
            "candidate_replication_keys": [
                key
                for key in field_summary
                if any(token in key.lower() for token in ("changed", "modified", "updated", "date"))
            ],
        }

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\nWrote {summary_path}")
    print("\nNext steps:")
    print("  1. Inspect sample_responses/*.json")
    print("  2. Fix _extract_records() if record_count is 0 but raw JSON has data")
    print("  3. Tighten stream schemas and primary/replication keys from summary.json")
    print("  4. Copy sanitized fixtures into tests/fixtures/ for unit tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
