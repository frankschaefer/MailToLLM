"""Tests for improved phone number extraction."""
from mailtollm.services.entity_extractor import extract_entities


def test_extract_international_phone_with_plus() -> None:
    """Test extracting international phone numbers with + prefix."""
    text = "Call me at +41 44 123 45 67 for details."
    entities = extract_entities(text)
    assert "+41 44 123 45 67" in entities.phones


def test_extract_international_phone_compact() -> None:
    """Test extracting compact international format."""
    text = "My number is +1-555-123-4567 and +49-30-12345678"
    entities = extract_entities(text)
    assert "+1-555-123-4567" in entities.phones
    assert "+49-30-12345678" in entities.phones


def test_extract_country_code_format() -> None:
    """Test extracting phone with 00 country code."""
    text = "Contact: 0041 44 123 45 67"
    entities = extract_entities(text)
    assert "0041 44 123 45 67" in entities.phones


def test_extract_local_phone_with_area_code() -> None:
    """Test extracting local phone with area code."""
    text = "Call us: 044-1234567 or (044) 123 45 67"
    entities = extract_entities(text)
    # Should match at least one valid phone
    assert len(entities.phones) >= 1


def test_reject_address_street_number_postal_code() -> None:
    """Test that address components are NOT extracted as phone numbers."""
    text = "Address: Stockerstrasse 44\n8002 Zurich"
    entities = extract_entities(text)
    # Should NOT extract "44 8002" as phone number
    assert "44\n8002" not in entities.phones
    assert "44 8002" not in entities.phones


def test_reject_date_as_phone() -> None:
    """Test that dates are NOT extracted as phone numbers."""
    text = "Meeting on 07.01.2026 at 10:00"
    entities = extract_entities(text)
    assert "07.01.2026" not in entities.phones


def test_reject_postal_code_house_number() -> None:
    """Test that postal code + house number patterns are rejected."""
    text = "8002 44"  # Postal code + street number
    entities = extract_entities(text)
    assert len(entities.phones) == 0


def test_reject_too_few_digits() -> None:
    """Test that numbers with too few digits are rejected."""
    text = "Call 123-4567"  # Only 7 digits
    entities = extract_entities(text)
    assert len(entities.phones) == 0


def test_reject_too_many_digits() -> None:
    """Test that numbers with too many digits are rejected."""
    text = "ID: 1234567890123456"  # 16 digits - too many
    entities = extract_entities(text)
    assert len(entities.phones) == 0


def test_extract_multiple_valid_phones() -> None:
    """Test extracting multiple valid phone numbers."""
    text = "Office: +41 44 123 45 67, Mobile: +41 79 123 45 67"
    entities = extract_entities(text)
    assert len(entities.phones) == 2


def test_extract_phone_with_parentheses() -> None:
    """Test extracting phone with parentheses around area code."""
    text = "Contact: (044) 123 45 67"
    entities = extract_entities(text)
    assert len(entities.phones) >= 1


def test_extract_phone_with_slash_separator() -> None:
    """Test extracting phone with slash separator."""
    text = "Phone: 044/123 45 67"
    entities = extract_entities(text)
    assert len(entities.phones) >= 1


def test_no_false_positives_in_real_email() -> None:
    """Test with real-world email content to ensure no false positives."""
    text = """
    Dear Sir,

    Please visit our office at:
    Stockerstrasse 44
    8002 Zurich
    Switzerland

    Or call us: +41 44 123 45 67

    Best regards
    """
    entities = extract_entities(text)

    # Should extract the phone number
    assert any("+41 44 123 45 67" in phone for phone in entities.phones)

    # Should NOT extract address components
    assert not any("44" in phone and "8002" in phone for phone in entities.phones)
