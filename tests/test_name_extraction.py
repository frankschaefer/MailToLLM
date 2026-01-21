"""Tests for name extraction from email addresses."""
from mailtollm.core.pipeline import _guess_name_from_email


def test_guess_name_from_simple_email() -> None:
    """Test extracting name from simple firstname.lastname format."""
    assert _guess_name_from_email("john.doe@example.com") == "John Doe"
    assert _guess_name_from_email("alice.smith@company.de") == "Alice Smith"


def test_guess_name_from_hyphenated_email() -> None:
    """Test extracting name with hyphens."""
    assert _guess_name_from_email("alice-wonderland@example.com") == "Alice Wonderland"
    assert _guess_name_from_email("mary-jane-watson@example.com") == "Mary Jane Watson"


def test_guess_name_from_underscore_email() -> None:
    """Test extracting name with underscores."""
    assert _guess_name_from_email("john_doe@example.com") == "John Doe"


def test_guess_name_from_initials() -> None:
    """Test extracting initials."""
    assert _guess_name_from_email("j.smith@example.com") == "J Smith"
    assert _guess_name_from_email("a.b.c@example.com") == "A B C"


def test_guess_name_skips_generic_emails() -> None:
    """Test that generic/role-based emails return None."""
    assert _guess_name_from_email("info@company.com") is None
    assert _guess_name_from_email("admin@company.com") is None
    assert _guess_name_from_email("support@company.com") is None
    assert _guess_name_from_email("contact@company.com") is None
    assert _guess_name_from_email("hello@company.com") is None
    assert _guess_name_from_email("sales@company.com") is None
    assert _guess_name_from_email("noreply@company.com") is None
    assert _guess_name_from_email("no-reply@company.com") is None


def test_guess_name_handles_invalid_emails() -> None:
    """Test that invalid emails are handled gracefully."""
    assert _guess_name_from_email("") is None
    assert _guess_name_from_email("notanemail") is None
    assert _guess_name_from_email("@example.com") is None


def test_guess_name_skips_complex_emails() -> None:
    """Test that overly complex email addresses return None."""
    # Too many parts (likely not a person name)
    assert _guess_name_from_email("a.b.c.d.e.f@example.com") is None
