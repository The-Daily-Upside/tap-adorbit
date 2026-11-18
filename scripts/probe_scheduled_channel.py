"""Find which Ad Orbit endpoint actually fills scheduledChannel.

Loads TAP_ADORBIT_INSTANCE, TAP_ADORBIT_PUBLIC_KEY, and TAP_ADORBIT_PRIVATE_KEY
from the Meltano project .env. Key values are never printed.

    python scripts/probe_scheduled_channel.py

Inside the meltano container that file is
/app/projects/meltano-the-daily-upside/tdu-meltano/.env. On the host it is the
same project checked out next to this repo. Pass --env to override the path.

Prints the HATEOAS root keys, then fetches one small page from any endpoint
whose name looks like a reserved item, ticket, or channel. For each page it
reports how scheduledChannel is typed and prints one non-null sample.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tap_adorbit.client import AdOrbitClient

CONTAINER_ENV = Path("/app/projects/meltano-the-daily-upside/tdu-meltano/.env")
SIBLING_ENV = (
    Path(__file__).resolve().parents[2]
    / "meltano-the-daily-upside"
    / "tdu-meltano"
    / ".env"
)


def load_env(path: Path) -> dict[str, str]:
    """Read KEY=VALUE lines. Does not export them or log values."""
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        values[key.strip()] = value
    return values


def resolve_env_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    if CONTAINER_ENV.is_file():
        return CONTAINER_ENV
    return SIBLING_ENV

INTERESTING = ("reserv", "channel", "ticket", "digital", "item", "service")
CHANNEL_KEYS = ("scheduledChannel", "scheduled_channel", "channel")
SAMPLE_LIMIT = 5


def walk(node: Any, path: str = "$"):
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}"
            if key in CHANNEL_KEYS:
                yield child, value
            yield from walk(value, child)
    elif isinstance(node, list):
        for index, value in enumerate(node[:20]):
            yield from walk(value, f"{path}[{index}]")


def describe(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        text = value.replace("\n", " ")
        return f"string len={len(value)} {text[:120]!r}"
    if isinstance(value, (int, float, bool)):
        return f"{type(value).__name__} {value!r}"
    if isinstance(value, dict):
        return f"object keys={list(value.keys())[:12]}"
    if isinstance(value, list):
        return f"array len={len(value)}"
    return type(value).__name__


def records_from(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
        return [payload]
    return []


def line_item_ids(node: Any, found: list[str]) -> None:
    """Collect service-sale ids from an order payload."""
    if isinstance(node, dict):
        if "id" in node and any(
            key in node for key in ("serviceName", "serviceId", "scheduledChannel")
        ):
            found.append(str(node["id"]))
        for value in node.values():
            line_item_ids(value, found)
    elif isinstance(node, list):
        for value in node:
            line_item_ids(value, found)


def probe_reserved_items(client: AdOrbitClient, root: dict[str, Any]) -> None:
    """Fetch known service sales, then the reserved-item record for each id."""
    order_template = root.get("order")
    if not isinstance(order_template, str):
        print("\nNo order URL in root; skipping reserved-item lookup.")
        return

    item_templates = [
        ("media-reserved-item", root.get("media-reserved-item")),
        ("service-item", root.get("service-item")),
    ]
    # Order 2735 is a service-sale order we already inspected in Postgres.
    order_ids = ["2735"]
    print(f"\nFetching orders {order_ids} for service-sale ids")
    sale_ids: list[str] = []
    for order_id in order_ids:
        url = order_template.replace("{id}", order_id)
        try:
            payload = client.request("GET", url)
        except Exception as exc:
            print(f"order {order_id} ERROR: {exc}")
            continue
        ids: list[str] = []
        line_item_ids(payload, ids)
        print(f"order {order_id} service-sale ids: {ids[:8]}")
        sale_ids.extend(ids)

    seen: set[str] = set()
    for sale_id in sale_ids:
        if sale_id in seen:
            continue
        seen.add(sale_id)
        if len(seen) > 3:
            break
        for name, template in item_templates:
            if not isinstance(template, str) or "{id}" not in template:
                continue
            probe_endpoint(client, f"{name} {sale_id}", template.replace("{id}", sale_id))


def probe_endpoint(client: AdOrbitClient, key: str, url: str) -> None:
    print(f"\n--- {key} ---")
    print(f"url: {url}")
    try:
        payload = client.request(
            "GET",
            url,
            extra_headers={"X-OPT-LIMIT": str(SAMPLE_LIMIT), "X-OPT-OFFSET": "0"},
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return

    rows = records_from(payload)
    print(f"records: {len(rows)}")
    if rows:
        print(f"record keys: {sorted(rows[0].keys())}")

    found = list(walk(payload))
    if not found:
        print("scheduledChannel: key not present")
        return

    counts: Counter[str] = Counter()
    sample = None
    for path, value in found:
        kind = "null" if value is None else type(value).__name__
        counts[f"{path}={kind}"] += 1
        if sample is None and value not in (None, "", [], {}):
            sample = (path, value)
    print("channel fields:")
    for label, count in counts.most_common(12):
        print(f"  {label} x{count}")
    if sample:
        path, value = sample
        print(f"non-null sample at {path}: {describe(value)}")
    else:
        print("non-null sample: none on this page")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Probe Ad Orbit for scheduledChannel.")
    parser.add_argument(
        "--env",
        default=None,
        help="Path to tdu-meltano/.env (default: container path, then sibling checkout)",
    )
    args = parser.parse_args()

    env_path = resolve_env_path(args.env)
    if not env_path.is_file():
        print(f"Meltano .env not found: {env_path}", file=sys.stderr)
        return 1

    env = load_env(env_path)
    instance = env.get("TAP_ADORBIT_INSTANCE", "")
    public_key = env.get("TAP_ADORBIT_PUBLIC_KEY", "")
    private_key = env.get("TAP_ADORBIT_PRIVATE_KEY", "")
    missing = [
        name
        for name, value in (
            ("TAP_ADORBIT_INSTANCE", instance),
            ("TAP_ADORBIT_PUBLIC_KEY", public_key),
            ("TAP_ADORBIT_PRIVATE_KEY", private_key),
        )
        if not value
    ]
    if missing:
        print(f"Missing from {env_path}: {', '.join(missing)}", file=sys.stderr)
        return 1

    print(f"Loaded Ad Orbit settings from {env_path}")
    client = AdOrbitClient(
        instance=instance,
        public_key=public_key,
        private_key=private_key,
    )
    print(f"Base URL: {client.base_url}")
    root = client.get_root()
    print(f"\nroot keys ({len(root)}):")
    for key in sorted(root):
        value = root[key]
        shown = value if isinstance(value, str) else json.dumps(value)[:160]
        print(f"  {key}: {shown}")

    interesting = [
        key
        for key in sorted(root)
        if any(token in key.lower() for token in INTERESTING)
    ]
    list_keys = []
    for key in interesting:
        value = root[key]
        if isinstance(value, str) and "{" not in value:
            list_keys.append(key)
    print(f"\nprobing {len(list_keys)} list endpoints: {list_keys or '(none)'}")
    for key in list_keys:
        probe_endpoint(client, key, root[key])

    probe_reserved_items(client, root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
