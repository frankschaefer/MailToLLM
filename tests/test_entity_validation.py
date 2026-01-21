"""Tests for entity extraction validation (emails, phones, etc.)."""
from __future__ import annotations

from mailtollm.services.entity_extractor import (
    _is_valid_email,
    _is_valid_phone,
    _extract_and_validate_emails,
    _extract_and_validate_phones,
)


# ============================================================================
# Email Validation Tests
# ============================================================================

def test_valid_email_addresses() -> None:
    """Test that legitimate email addresses pass validation."""
    assert _is_valid_email("alice@example.com") is True
    assert _is_valid_email("bob.jones@company.co.uk") is True
    assert _is_valid_email("test+tag@domain.org") is True
    assert _is_valid_email("user_name@test-domain.de") is True


def test_invalid_email_image_references() -> None:
    """Test that image references are rejected."""
    # Real example from user's data
    assert _is_valid_email("image001.jpg@01DC742F.BBA") is False
    assert _is_valid_email("photo.png@ABC123.XYZ") is False
    assert _is_valid_email("file.jpeg@DEADBEEF.COM") is False


def test_invalid_email_suspicious_domains() -> None:
    """Test that suspicious hex-like domains are rejected."""
    assert _is_valid_email("test@01DC742F.BBA") is False
    assert _is_valid_email("user@ABCDEF12.XYZ") is False


def test_invalid_email_no_tld() -> None:
    """Test that emails without valid TLD are rejected."""
    assert _is_valid_email("test@localhost") is False
    assert _is_valid_email("user@domain") is False


def test_invalid_email_numeric_tld() -> None:
    """Test that emails with numeric TLDs are rejected."""
    assert _is_valid_email("test@example.123") is False
    assert _is_valid_email("user@domain.456") is False


def test_invalid_email_too_long_tld() -> None:
    """Test that emails with overly long TLDs are rejected."""
    assert _is_valid_email("test@example.verylongtld") is False


def test_extract_and_filter_emails() -> None:
    """Test email extraction with filtering."""
    text = """
    Contact us at:
    - Valid: alice@example.com
    - Valid: bob@company.co.uk
    - Invalid: image001.jpg@01DC742F.BBA
    - Invalid: photo@ABCD1234.XYZ
    """
    emails = _extract_and_validate_emails(text)

    assert len(emails) == 2
    assert "alice@example.com" in emails
    assert "bob@company.co.uk" in emails
    assert "image001.jpg@01DC742F.BBA" not in emails


# ============================================================================
# Phone Number Validation Tests
# ============================================================================

def test_valid_phone_numbers() -> None:
    """Test that legitimate phone numbers pass validation."""
    assert _is_valid_phone("+49 123 456 789") is True
    assert _is_valid_phone("+1 (555) 123-4567") is True
    assert _is_valid_phone("0123456789") is True
    assert _is_valid_phone("+49-89-123456") is True


def test_invalid_phone_date_formats() -> None:
    """Test that date formats are rejected as phone numbers."""
    # Real example from user's data
    assert _is_valid_phone("07.01.2026") is False
    assert _is_valid_phone("01.12.2025") is False
    assert _is_valid_phone("31/12/2025") is False
    assert _is_valid_phone("2025-12-31") is False


def test_invalid_phone_too_few_digits() -> None:
    """Test that strings with too few digits are rejected."""
    assert _is_valid_phone("12345") is False  # Only 5 digits
    assert _is_valid_phone("+1-234") is False  # Only 4 digits


def test_invalid_phone_too_many_separators() -> None:
    """Test that date-like patterns with many separators are rejected."""
    assert _is_valid_phone("12.34.56.78") is False  # 3 dots
    assert _is_valid_phone("1/2/3456") is False  # 2 slashes


def test_extract_and_filter_phones() -> None:
    """Test phone extraction with filtering."""
    text = """
    Call us:
    - Valid: +49 123 456 789
    - Valid: (555) 123-4567
    - Invalid: 07.01.2026 (this is a date)
    - Invalid: 12.34.5678 (looks like date)
    """
    phones = _extract_and_validate_phones(text)

    # Should have the valid phone numbers, not the dates
    valid_count = sum(1 for p in phones if len([c for c in p if c.isdigit()]) >= 6)
    assert valid_count >= 1

    # Dates should be filtered out
    assert "07.01.2026" not in phones


def test_phone_validation_edge_cases() -> None:
    """Test edge cases in phone validation."""
    # Exactly 6 digits - should pass
    assert _is_valid_phone("123456") is True

    # International format with many spaces - should pass
    assert _is_valid_phone("+1 234 567 8900") is True

    # Date with 4-digit year - should fail
    assert _is_valid_phone("2025.12.31") is False


# ============================================================================
# Integration Tests
# ============================================================================

def test_extract_entities_filters_invalid_data() -> None:
    """Test that extract_entities filters out invalid emails and phones."""
    from mailtollm.services.entity_extractor import extract_entities

    text = """
    Email me at alice@example.com or bob@company.de
    Don't use image001.jpg@01DC742F.BBA - that's not an email!

    Call us at +49 123 456 789
    Meeting on 07.01.2026 at the office.
    """

    entities = extract_entities(text)

    # Should have valid emails only
    assert "alice@example.com" in entities.emails
    assert "bob@company.de" in entities.emails
    assert "image001.jpg@01DC742F.BBA" not in entities.emails

    # Should have valid phones only (not dates)
    phone_digits = [sum(c.isdigit() for c in p) for p in entities.phones]
    assert all(d >= 6 for d in phone_digits)  # All phones have at least 6 digits

    # Date should not be in phones
    assert "07.01.2026" not in entities.phones
