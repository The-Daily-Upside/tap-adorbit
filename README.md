# tap-adorbit

`tap-adorbit` is a Singer tap for the [Ad Orbit](https://www.adorbit.com/) publishing platform, built with the Meltano SDK.

## Supported streams

| Stream | Endpoint | Replication key |
|--------|----------|-----------------|
| `companies` | `/companies` | `company_updated_date` |
| `contacts` | `/contacts` | `contact_updated_date` |
| `activities` | `/activities` | `modified` |
| `orders` | `/orders` | `order_modified` |
| `subscribers` | `/subscribers` | — |
| `subscriptions` | `/subscriptions` | — |
| `subscriptionplans` | `/subscriptionplans` | `expiration_date` |
| `publications` | `/publications` | — |
| `editorials` | `/editorials` | — |
| `vendors` | `/vendors` | — |
| `companyassets` | `/companyassets` | — |

Each stream declares explicit columns from live API probes plus a `_raw` JSON column containing the full API record. This ensures `target-postgres` loads typed fields while preserving future or tenant-specific fields in `_raw`.

## Installation

```bash
pip install -e .
# or
pipx install .
```

## Configuration

| Setting | Required | Description |
|---------|----------|-------------|
| `instance` | Yes | Ad Orbit instance name (e.g. `thedailyupside` for `thedailyupside.api.adorbit.com`) |
| `public_key` | Yes | Public API key from Administration → User |
| `private_key` | Yes | Private API key from Administration → User |
| `start_date` | No | Incremental sync timestamp (`YYYY-MM-DD HH:MM:SS`) sent as `changedsince` |
| `page_size` | No | Records per page via `X-OPT-LIMIT` (default: 100) |
| `api_scheme` | No | `https` or `http` (default: `https`) |

Example `meltano.yml`:

```yaml
plugins:
  extractors:
    - name: tap-adorbit
      namespace: tap_adorbit
      executable: tap-adorbit
      settings:
        instance: "your-instance"
        public_key: "YOUR_PUBLIC_KEY"
        private_key: "YOUR_PRIVATE_KEY"
        start_date: "2025-01-01 00:00:00"
        page_size: 100
```

## Usage

```bash
# Discover available streams and schemas
tap-adorbit --config config.json --discover

# Run a sync
tap-adorbit --config config.json
```

With Meltano:

```bash
meltano invoke tap-adorbit --discover
meltano run tap-adorbit target-postgres-adorbit
```

After changing stream schemas, run a full refresh so Postgres creates the new columns:

```bash
meltano run tap-adorbit target-postgres-adorbit --full-refresh
```

## Soft deletes and team-facing views

The tap sets `is_deleted` on every row (see [docs/VIEWS.md](docs/VIEWS.md) for rules). Dagster should create `adorbit.v_*` views that filter deleted rows and unpack JSON fields. Raw `adorbit.*` tables are for pipelines; point analysts at the views.

## Authentication

Ad Orbit supports OAuth 2.0 (documented in the official API guide) and API key pairs. This tap uses **API key authentication** with HMAC-SHA512 request signing:

1. Build a message: `{HTTP_METHOD}\n{full_request_uri}` (including query string)
2. Sign it with the private key using HMAC-SHA512 (hex digest, base64-encoded)
3. Send the `Authorization` header: `ADORBIT {public_key}:{signature}`

API keys are found in the Ad Orbit application under **Administration → User**.

## Pagination and incremental sync

List endpoints are paginated with:

- `X-OPT-LIMIT` / `X-OPT-OFFSET` headers (0-based page index; offset=2 with limit=10 returns records 21–30)
- `changedsince` query parameter and `X-OPT-CHANGEDSINCE` header for incremental sync

Replication keys match the official field names where documented (`company_updated_date`, `contact_updated_date`, `order_modified`, `modified`).

## Developing schemas from real API responses

Schemas in `tap_adorbit/schemas.py` are generated from `sample_responses/summary.json`. To refresh after API changes:

```bash
cp config.example.json config.json   # fill in real keys
python scripts/probe_adorbit.py
```

Then update `STREAM_FIELDS` in `tap_adorbit/schemas.py` from the new `summary.json` field inventories.

## API documentation alignment

See [docs/API_ALIGNMENT.md](docs/API_ALIGNMENT.md) for how this tap maps to the official Ad Orbit API v26.4 documentation.

## License

MIT — see [LICENSE](LICENSE).
