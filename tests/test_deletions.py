"""Tests for soft-delete detection."""

from tap_adorbit.streams import AdOrbitStream


def test_companies_inactive_are_deleted():
    assert AdOrbitStream._compute_is_deleted("companies", {"active": False}) is True
    assert AdOrbitStream._compute_is_deleted("companies", {"active": True}) is False


def test_contacts_inactive_are_deleted():
    assert AdOrbitStream._compute_is_deleted("contacts", {"active": None}) is True


def test_activities_deleted_flag():
    assert AdOrbitStream._compute_is_deleted("activities", {"deleted": "1"}) is True
    assert AdOrbitStream._compute_is_deleted("activities", {"deleted": "0"}) is False


def test_publications_inactive_string():
    assert AdOrbitStream._compute_is_deleted("publications", {"active": "0"}) is True
    assert AdOrbitStream._compute_is_deleted("publications", {"active": "1"}) is False


def test_normalize_record_sets_is_deleted():
    record = {"id": "1", "name": "Acme", "active": False}
    normalized = AdOrbitStream._normalize_record(record, "companies")
    assert normalized["is_deleted"] is True
