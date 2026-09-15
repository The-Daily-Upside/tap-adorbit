# Ad Orbit API alignment (v26.4)

Cross-check of `tap-adorbit` against the official Ad Orbit API developer documentation (April 2026).

## Authentication

| Doc | Tap implementation | Status |
|-----|-------------------|--------|
| OAuth 2.0 via `id.api.adorbit.com` (recommended) | Not implemented | Future option |
| API keys via `{instance}.api.adorbit.com` | HMAC-SHA512 `ADORBIT {public_key}:{signature}` | Working (not in PDF; live API behavior) |

The PDF documents OAuth in detail but only mentions API key pairs briefly. HMAC signing is required for API key access on instance URLs and is confirmed working against `thedailyupside.api.adorbit.com`.

## Pagination and incremental filters

| Doc | Tap implementation | Status |
|-----|-------------------|--------|
| `changedsince` query param on list endpoints | Sent as query param **and** `X-OPT-CHANGEDSINCE` header | Aligned |
| `limit` / `offset` query params (some endpoints) | `X-OPT-LIMIT` / `X-OPT-OFFSET` headers | Working on list endpoints |
| Offset is 0-based **page** index | `offset += 1` between pages | Aligned |

Companies, contacts, and orders document `changedsince` with format `YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS`. Orders doc also shows `YY-MM-DD` (likely typo).

## Streams vs documented endpoints

| Stream | Doc section | Notes |
|--------|-------------|-------|
| `companies` | GET `/companies` | Schema matches `GetCompany` fields from probe |
| `contacts` | GET `/contacts` | `contact_updated_date` used for incremental (probe-confirmed) |
| `activities` | GET `/activities` | `modified` replication key per `GetActivity` |
| `orders` | GET `/orders` | `order_modified` per order schema; `changedsince` filter documented |
| `subscribers` | GET `/subscribers` | Empty in TDU instance; minimal schema + `_raw` |
| `subscriptions` | GET `/subscriptions` | Empty in TDU instance; minimal schema + `_raw` |
| `subscriptionplans` | Not in PDF | Exists in HATEOAS root; returns `assets` collection |
| `publications` | GET `/publications` | No incremental filter documented |
| `editorials` | Not in PDF | Exists in HATEOAS root as `/editorials` |
| `vendors` | Not in PDF | Exists in HATEOAS root as `/vendors` |
| `companyassets` | Not in PDF | Exists in HATEOAS root; returns `assets` collection |

## Schema strategy

Official docs describe response shapes for single-record endpoints (`GetCompany`, etc.). List endpoints return the same field sets. The tap:

1. Declares all probe-discovered fields as typed Postgres columns
2. Serializes nested objects/arrays (`links`, `primary_contact`, `serviceSales`) to JSON strings
3. Stores the untouched API payload in `_raw` for fields not yet in the typed schema

`target-postgres` ignores undeclared schema properties, so `_raw` is required for forward compatibility.

## Documented endpoints not yet synced

The HATEOAS root exposes many additional resources (opportunities, forecasts, proposals, tickets, analytics, projects, etc.) that are not part of this tap's initial scope. Add new streams by:

1. Probing the endpoint with `scripts/probe_adorbit.py`
2. Adding fields to `STREAM_FIELDS` in `schemas.py`
3. Creating a stream class in `streams.py`

## Known gaps

- **OAuth 2.0**: Not supported; API keys only
- **Empty streams**: `subscribers`, `subscriptions`, `editorials`, `vendors`, `companyassets` have minimal schemas until populated data is probed
- **Activities filters**: Doc supports `userid`, `date`, `sdate`, `edate` query filters; tap syncs all activities with `changedsince` only
