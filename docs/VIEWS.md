# Ad Orbit reporting views (Dagster)

Team-facing Postgres views over the `adorbit` schema. Dagster should own creation and grants.

## Conventions

| Item | Value |
|------|-------|
| Source schema | `adorbit` |
| View naming | `adorbit.v_{table}` (e.g. `adorbit.v_companies`) |
| Row filter | `WHERE is_deleted IS NOT TRUE` on every view |
| Exclude from views | `is_deleted`, `_raw` |
| JSON in base tables | Object/array API fields are stored as `text` (JSON strings) |
| JSON in views | Cast to `jsonb`; add extracted scalar columns where listed |

### Helper function

```sql
adorbit.parse_jsonb(value text) -> jsonb
-- NULL or blank -> NULL; otherwise value::jsonb
```

### `is_deleted` (set by tap)

| Stream | `is_deleted = true` when |
|--------|--------------------------|
| companies, contacts | `active IS NOT TRUE` |
| activities | `deleted = '1'` |
| publications, subscriptionplans, subscribers | `active` not in (`'1'`, `'true'`, `'yes'`) |
| subscriptions | `status = '3'` |
| orders, editorials, vendors, companyassets | always `false` (for now) |

### Column names

`target-postgres` lowercases property names. Confirm against `\d adorbit.companies` after first sync. Examples: `primaryrep`, `company_updated_date`, `primary_contact`.

---

## Views with typed columns + JSON unpacking

Pass through all scalar columns from the base table (except `is_deleted`, `_raw`), replace JSON text columns with `jsonb`, and add extracted columns.

### `adorbit.v_companies`

**Source:** `adorbit.companies`

**JSON columns → jsonb:**

| Base column | View column | Extracted columns |
|-------------|-------------|-------------------|
| `links` | `links` | `links_self` = `links->>'self'` |
| `primary_contact` | `primary_contact` | `primary_contact_name`, `primary_contact_link`, `primary_contact_phones` (= `->'phone'`) |
| `additionalreps` | `additional_reps` | — |
| `dynamicfields` | `dynamic_fields` | — |
| `last_activity` | `last_activity` | `last_activity_date`, `last_activity_type`, `last_activity_link` |

### `adorbit.v_contacts`

**Source:** `adorbit.contacts`

| Base column | View column | Extracted columns |
|-------------|-------------|-------------------|
| `links` | `links` | `links_self` |
| `dynamicfields` | `dynamic_fields` | — |

### `adorbit.v_activities`

**Source:** `adorbit.activities`

| Base column | View column | Extracted columns |
|-------------|-------------|-------------------|
| `links` | `links` | `links_self` |
| `activity_contact` | `activity_contact` | `activity_contact_name` |

### `adorbit.v_orders`

**Source:** `adorbit.orders`

| Base column | View column |
|-------------|-------------|
| `links` | `links` (+ `links_self`) |
| `servicesales` | `service_sales` |
| `dynamicattributes` | `dynamic_attributes` |
| `adsales` | `ad_sales` |
| `installmentpayments` | `installment_payments` |
| `customerapprovaldocument` | `customer_approval_document` |

### `adorbit.v_publications`

**Source:** `adorbit.publications`

| Base column | View column | Extracted columns |
|-------------|-------------|-------------------|
| `links` | `links` | `links_self` |

### `adorbit.v_subscriptionplans`

**Source:** `adorbit.subscriptionplans`

No JSON columns. All scalar columns + `_sdc_*` metadata. Filter only.

---

## Views with `_raw` unpack (minimal schemas)

Streams with only `id` (+ `is_deleted`, `_raw`) in the base table. Expose the full API record as jsonb.

| View | Source table | Columns |
|------|--------------|---------|
| `adorbit.v_subscribers` | `subscribers` | `id`, `record` (= `parse_jsonb(_raw)`), `_sdc_*` |
| `adorbit.v_subscriptions` | `subscriptions` | same |
| `adorbit.v_editorials` | `editorials` | same |
| `adorbit.v_vendors` | `vendors` | same |
| `adorbit.v_companyassets` | `companyassets` | same |

Query example: `SELECT id, record->>'email' FROM adorbit.v_subscribers`

---

## Full view list

| Base table | Reporting view |
|------------|----------------|
| `adorbit.activities` | `adorbit.v_activities` |
| `adorbit.companies` | `adorbit.v_companies` |
| `adorbit.contacts` | `adorbit.v_contacts` |
| `adorbit.orders` | `adorbit.v_orders` |
| `adorbit.publications` | `adorbit.v_publications` |
| `adorbit.subscriptionplans` | `adorbit.v_subscriptionplans` |
| `adorbit.subscribers` | `adorbit.v_subscribers` |
| `adorbit.subscriptions` | `adorbit.v_subscriptions` |
| `adorbit.editorials` | `adorbit.v_editorials` |
| `adorbit.vendors` | `adorbit.v_vendors` |
| `adorbit.companyassets` | `adorbit.v_companyassets` |

## Grants (suggested)

Grant `SELECT` on `adorbit.v_*` to `bi_user`, `bigquery_user`. Raw `adorbit.*` tables optional for admins/pipelines only.

## Dagster notes

- Run after Meltano sync creates/updates `adorbit` tables.
- Re-run when tap adds columns (views with explicit column lists need updating).
- `parse_jsonb` is safe on NULL/empty strings.
- Periodic full refresh on the tap catches hard-deleted API records that never flip `is_deleted`.
