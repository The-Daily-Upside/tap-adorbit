"""Explicit stream schemas for target-postgres compatibility.

target-postgres only creates columns for properties declared in the SCHEMA
message; additionalProperties are ignored at load time. Each stream therefore
declares known API fields as typed columns plus a ``_raw`` JSON backup of the
full API record so future/tenant-specific fields are never lost.
"""

from typing import Dict

from singer_sdk import typing as th

# Field inventories from live API probe (sample_responses/summary.json).
STREAM_FIELDS: Dict[str, Dict[str, str]] = {
    "activities": {
        "active": "string",
        "activity_contact": "null",
        "assignedID": "string",
        "assignedName": "string",
        "call_duration": "integer",
        "categoryID": "string",
        "categoryName": "null",
        "categoryTypeID": "string",
        "categoryTypeName": "string",
        "collections": "string",
        "company": "string",
        "companyId": "string",
        "company_xref": "null",
        "complete": "string",
        "contactId": "string",
        "created": "string",
        "creatorID": "string",
        "creatorName": "string",
        "date": "string",
        "deleted": "string",
        "emailRecipients": "string",
        "endDate": "string",
        "endTime": "string",
        "eventETag": "string",
        "eventID": "string",
        "eventSummary": "string",
        "forecastID": "string",
        "id": "string",
        "links": "object",
        "meetingUrl": "null",
        "modified": "string",
        "note": "string",
        "opportunityID": "null",
        "opportunity_level": "null",
        "opportunity_name": "null",
        "paymentAmount": "string",
        "paymentDate": "string",
        "priority": "string",
        "publisherName": "string",
        "queuedEmailID": "string",
        "site_url": "string",
        "status": "string",
        "time": "string",
        "typeID": "string",
        "typeName": "string",
    },
    "companies": {
        "active": "boolean",
        "additionalReps": "array<object>|null",
        "address1": "null|string",
        "address2": "null|string",
        "artworkContactId": "string",
        "billingContact": "null",
        "billingContactId": "string",
        "city": "null|string",
        "collections": "string",
        "company_created_date": "string",
        "company_credit": "string",
        "company_updated_date": "string",
        "country": "string",
        "digitalArtworkContactId": "null",
        "dynamicFields": "null|object",
        "facebook_url": "null",
        "id": "string",
        "last_activity": "null|object",
        "linkedin_url": "null|string",
        "links": "object",
        "market": "string",
        "name": "string",
        "paymentTermId": "string",
        "primaryCatId": "string",
        "primaryRep": "string",
        "primaryRepId": "string",
        "primary_contact": "object",
        "publisherId": "string",
        "qbo_tax_rate_id": "null",
        "site_url": "string",
        "special_note": "null",
        "state": "null|string",
        "tax_id": "null|string",
        "twitter_url": "null",
        "type": "string",
        "website": "string",
        "xref": "null|string",
        "zipCode": "null|string",
    },
    "contacts": {
        "active": "boolean",
        "address1": "null|string",
        "address2": "null|string",
        "alternatePhoneNumber": "null|string",
        "alternatePhoneNumberExtension": "null|string",
        "cellPhoneNumber": "string",
        "city": "null|string",
        "company": "null|string",
        "companyId": "null|string",
        "company_xref": "null|string",
        "contact_created_date": "string",
        "contact_created_id": "string",
        "contact_email_updated_date": "null",
        "contact_lead_source": "null",
        "contact_lead_source_name": "null",
        "contact_lead_status": "null|string",
        "contact_lead_status_name": "null|string",
        "contact_notes": "null|string",
        "contact_owner_id": "string",
        "contact_phone_primary_ext": "null",
        "contact_proxy_company": "null|string",
        "contact_type": "string",
        "contact_updated_date": "null|string",
        "contact_xref": "string",
        "country": "string",
        "dynamicFields": "null|object",
        "emailAddress": "string",
        "facebook_url": "null|string",
        "faxNumber": "null|string",
        "firstName": "string",
        "id": "string",
        "isPrimaryContact": "string",
        "lastName": "string",
        "linkedin_url": "null|string",
        "links": "object",
        "name": "string",
        "officePhoneNumber": "null|string",
        "officePhoneNumberExtension": "null|string",
        "primaryPhoneNumberExtension": "null|string",
        "publisherName": "null|string",
        "referral_code": "null",
        "site_url": "string",
        "state": "string",
        "twitter_url": "null",
        "zipCode": "null|string",
    },
    "orders": {
        "adSales": "null",
        "agencyID": "string",
        "agencyXref": "null",
        "artworkContactId": "string",
        "artworkContactXref": "string",
        "assignedToEmail": "string",
        "assignedToId": "string",
        "assignedToName": "string",
        "billingCompanyId": "string",
        "billingCompanyXref": "string",
        "billingContactId": "string",
        "billingContactXref": "string",
        "client_approved_date": "string",
        "comments": "string",
        "company": "string",
        "companyID": "string",
        "companyXref": "string",
        "createDate": "string",
        "customerApprovalDocument": "null",
        "digitalArtworkContactId": "string",
        "digitalArtworkContactXref": "string",
        "dynamicAttributes": "null",
        "financeComments": "string",
        "finance_approved_date": "string",
        "id": "string",
        "installmentPayments": "null",
        "internalComments": "string",
        "is_historical_import": "string",
        "links": "object",
        "order_modified": "string",
        "poNumber": "null",
        "primaryContactCompanyXref": "string",
        "primaryContactEmail": "string",
        "primaryContactId": "string",
        "primaryContactName": "string",
        "primaryContactXref": "string",
        "probability": "string",
        "publisherName": "string",
        "publisher_approved": "string",
        "salesforceId": "null",
        "serviceSales": "array<object>",
        "soldDate": "string",
        "special_billing": "string",
        "templateName": "string",
        "xref": "string",
    },
    "publications": {
        "active": "string",
        "brandID": "null|string",
        "brandName": "null|string",
        "finance": "null|string",
        "id": "string",
        "links": "object",
        "name": "string",
        "online": "string",
        "publisherID": "string",
        "publisherName": "string",
        "useForMedia": "string",
    },
    "subscriptionplans": {
        "active": "string",
        "auto_renew": "string",
        "cost": "string",
        "duration_months": "string",
        "expiration_date": "null",
        "id": "string",
        "name": "string",
        "promo_code": "null",
        "publication_id": "string",
    },
}

MINIMAL_STREAM_FIELDS: Dict[str, str] = {
    "id": "string",
}


def _property_from_probe_type(name: str, type_str: str) -> th.Property:
    variants = set(type_str.split("|"))
    nullable = "null" in variants
    non_null = variants - {"null"}

    if not non_null:
        return th.Property(name, th.StringType(nullable=True))

    primary = sorted(non_null)[0]
    if primary == "boolean":
        return th.Property(name, th.BooleanType(nullable=nullable))
    if primary == "integer":
        return th.Property(name, th.IntegerType(nullable=nullable))
    if primary in {"object", "array<object>", "array"}:
        return th.Property(name, th.StringType(nullable=True))
    return th.Property(name, th.StringType(nullable=True))


def build_schema(fields: Dict[str, str]) -> dict:
    properties = [_property_from_probe_type(name, type_str) for name, type_str in sorted(fields.items())]
    properties.append(th.Property("is_deleted", th.BooleanType(nullable=False)))
    properties.append(th.Property("_raw", th.StringType(nullable=True)))
    return th.PropertiesList(*properties).to_dict()


def get_stream_schema(stream_name: str) -> dict:
    fields = STREAM_FIELDS.get(stream_name, MINIMAL_STREAM_FIELDS)
    return build_schema(fields)


STREAM_SCHEMAS = {stream: get_stream_schema(stream) for stream in STREAM_FIELDS}
STREAM_SCHEMAS.update(
    {
        "subscribers": build_schema(MINIMAL_STREAM_FIELDS),
        "subscriptions": build_schema(MINIMAL_STREAM_FIELDS),
        "editorials": build_schema(MINIMAL_STREAM_FIELDS),
        "vendors": build_schema(MINIMAL_STREAM_FIELDS),
        "companyassets": build_schema(MINIMAL_STREAM_FIELDS),
    }
)
