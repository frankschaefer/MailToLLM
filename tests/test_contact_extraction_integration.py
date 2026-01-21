"""Integration tests for contact extraction from email records."""
from __future__ import annotations

from pathlib import Path

from mailtollm.models.schema import EmailRecord, EntityIndex
from mailtollm.core.pipeline import (
    _entities_to_contacts,
    _extract_email_from_field,
    _extract_email_and_name_from_field,
)


def test_extract_email_from_plain_email() -> None:
    """Test extraction from plain email address."""
    assert _extract_email_from_field("alice@example.com") == "alice@example.com"


def test_extract_email_from_name_email_format() -> None:
    """Test extraction from 'Name <email>' format."""
    assert _extract_email_from_field("Alice Smith <alice@example.com>") == "alice@example.com"
    assert _extract_email_from_field("Bob Jones<bob@test.com>") == "bob@test.com"


def test_extract_email_from_name_only() -> None:
    """Test that names without emails return None."""
    assert _extract_email_from_field("Alice Smith") is None
    assert _extract_email_from_field("Tobias Kippenberg") is None
    assert _extract_email_from_field("Frank Schaefer") is None


def test_extract_email_from_empty() -> None:
    """Test extraction from empty/None values."""
    assert _extract_email_from_field("") is None
    assert _extract_email_from_field(None) is None
    assert _extract_email_from_field("   ") is None


def test_extract_email_and_name_from_name_email_format() -> None:
    """Test extraction of both name and email from 'Name <email>' format."""
    email, name = _extract_email_and_name_from_field("Alice Smith <alice@example.com>")
    assert email == "alice@example.com"
    assert name == "Alice Smith"

    email, name = _extract_email_and_name_from_field("Bob Jones <bob@test.com>")
    assert email == "bob@test.com"
    assert name == "Bob Jones"


def test_extract_email_and_name_from_plain_email() -> None:
    """Test that plain email returns no name."""
    email, name = _extract_email_and_name_from_field("alice@example.com")
    assert email == "alice@example.com"
    assert name is None


def test_extract_email_and_name_from_name_only() -> None:
    """Test that name-only returns no email or name."""
    email, name = _extract_email_and_name_from_field("Alice Smith")
    assert email is None
    assert name is None


def test_contact_extraction_from_email_with_multiple_recipients() -> None:
    """Test that sender and multiple recipients are extracted as contacts."""
    email = EmailRecord(
        id="email-1",
        subject="Test Subject",
        sender="anat.siddharth@deeplight.ai",
        recipients=[
            "tobias.kippenberg@example.com",
            "frank.schaefer@example.com",
        ],
        date="2025-11-13",
        body_text="Test body",
    )

    entities = EntityIndex(
        emails=[],
        organizations=[],
        people=[],
        phones=[],
        addresses=[],
    )

    contacts = _entities_to_contacts("email-1", entities, email)

    # Should have 3 contacts: 1 sender + 2 recipients
    assert len(contacts) == 3

    # Check sender
    sender_contact = [c for c in contacts if c.email == "anat.siddharth@deeplight.ai"][0]
    assert sender_contact.notes == "Email sender"

    # Check recipients
    recipient1 = [c for c in contacts if c.email == "tobias.kippenberg@example.com"][0]
    assert recipient1.notes == "Email recipient"

    recipient2 = [c for c in contacts if c.email == "frank.schaefer@example.com"][0]
    assert recipient2.notes == "Email recipient"


def test_contact_extraction_with_name_address_format() -> None:
    """Test extraction when recipients have name + email format - including NAMES."""
    email = EmailRecord(
        id="email-2",
        subject="Test",
        sender="Alice Smith <alice@example.com>",
        recipients=[
            "Bob Jones <bob@example.com>",
            "Carol White <carol@example.com>",
        ],
        date="2025-11-13",
        body_text="Test",
    )

    entities = EntityIndex()
    contacts = _entities_to_contacts("email-2", entities, email)

    # Should extract 3 contacts with BOTH emails AND names
    assert len(contacts) == 3

    # Check that email addresses AND names were extracted
    emails_and_names = [(c.email, c.name) for c in contacts]

    # Sender should have name extracted
    assert ("alice@example.com", "Alice Smith") in emails_and_names

    # Recipients should have names extracted
    assert ("bob@example.com", "Bob Jones") in emails_and_names
    assert ("carol@example.com", "Carol White") in emails_and_names


def test_contact_extraction_deduplicates_sender_and_recipient() -> None:
    """Test that same email as sender and recipient is only added once."""
    email = EmailRecord(
        id="email-3",
        subject="Test",
        sender="alice@example.com",
        recipients=["alice@example.com", "bob@example.com"],
        date="2025-11-13",
        body_text="Test",
    )

    entities = EntityIndex()
    contacts = _entities_to_contacts("email-3", entities, email)

    # alice@example.com appears as both sender and recipient
    # Should be added as sender first, then as recipient
    # Total: 3 contacts (sender alice, recipient alice, recipient bob)
    assert len(contacts) == 3

    alice_contacts = [c for c in contacts if c.email == "alice@example.com"]
    # Alice appears twice (as sender and recipient)
    assert len(alice_contacts) == 2


def test_contact_extraction_with_content_entities() -> None:
    """Test that emails from content are added but deduplicated against recipients."""
    email = EmailRecord(
        id="email-4",
        subject="Test",
        sender="alice@example.com",
        recipients=["bob@example.com"],
        date="2025-11-13",
        body_text="Contact charlie@example.com for details",
    )

    # Simulate entities extracted from body text
    entities = EntityIndex(
        emails=["bob@example.com", "charlie@example.com"],  # bob is duplicate, charlie is new
        organizations=["ACME Corp"],
        phones=["+49 123 456"],
        addresses=["Main Street 1"],
    )

    contacts = _entities_to_contacts("email-4", entities, email)

    # Should have: sender (alice), recipient (bob), content entity (charlie)
    # bob from entities should be skipped because already in recipients
    assert len(contacts) == 3

    emails = [c.email for c in contacts]
    assert "alice@example.com" in emails
    assert "bob@example.com" in emails
    assert "charlie@example.com" in emails

    # Check that charlie has phone and address from entities
    charlie = [c for c in contacts if c.email == "charlie@example.com"][0]
    assert charlie.notes == "Auto extracted from content"
    assert charlie.phone == "+49 123 456"
    assert charlie.address == "Main Street 1"
    assert charlie.organization == "ACME Corp"


def test_contact_extraction_no_recipients() -> None:
    """Test extraction when email has no recipients."""
    email = EmailRecord(
        id="email-5",
        subject="Test",
        sender="alice@example.com",
        recipients=[],
        date="2025-11-13",
        body_text="Test",
    )

    entities = EntityIndex()
    contacts = _entities_to_contacts("email-5", entities, email)

    # Should only have sender
    assert len(contacts) == 1
    assert contacts[0].email == "alice@example.com"
    assert contacts[0].notes == "Email sender"


def test_csv_reader_extracts_recipient_emails(tmp_path: Path) -> None:
    """Test that CSV reader correctly extracts recipient email addresses."""
    from mailtollm.io.csv_reader import read_email_csv

    # Create a CSV with multiple recipients
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(
        "From: (Address),To: (Address),CC: (Address),Subject,Body,Date\n"
        "sender@example.com,\"recipient1@example.com, recipient2@example.com\",cc@example.com,Test,Body,2025-11-13\n",
        encoding="utf-8"
    )

    records = read_email_csv(csv_path)

    assert len(records) == 1
    record = records[0]

    assert record["sender"] == "sender@example.com"
    # Should have 3 recipients: 2 from To field + 1 from CC field
    assert len(record["recipients"]) == 3
    assert "recipient1@example.com" in record["recipients"]
    assert "recipient2@example.com" in record["recipients"]
    assert "cc@example.com" in record["recipients"]


def test_csv_reader_handles_name_with_email_format(tmp_path: Path) -> None:
    """Test CSV reader with 'Name <email>' format in recipient fields."""
    from mailtollm.io.csv_reader import read_email_csv

    csv_path = tmp_path / "test.csv"
    csv_path.write_text(
        'From: (Name),From: (Address),To: (Name),To: (Address),Subject,Body,Date\n'
        'Alice Smith,alice@example.com,"Bob Jones, Carol White","bob@example.com, carol@example.com",Test,Body,2025-11-13\n',
        encoding="utf-8"
    )

    records = read_email_csv(csv_path)

    assert len(records) == 1
    record = records[0]

    # Should combine name and address
    assert "alice@example.com" in record["sender"]
    assert "Alice Smith" in record["sender"]

    # Recipients should have name + email combined
    assert len(record["recipients"]) == 2
    assert any("bob@example.com" in r for r in record["recipients"])
    assert any("carol@example.com" in r for r in record["recipients"])


def test_contact_extraction_with_name_only_recipients() -> None:
    """Test that recipients with only names (no email) are filtered out.

    This tests the scenario from the user's issue:
    'To: Tobias Kippenberg, Frank Schaefer' without email addresses.
    """
    email = EmailRecord(
        id="email-issue",
        subject="Test",
        sender="anat.siddharth@deeplight.ai",
        recipients=["Tobias Kippenberg", "Frank Schaefer"],  # Names only, no emails
        date="2025-11-13",
        body_text="Test",
    )

    entities = EntityIndex()
    contacts = _entities_to_contacts("email-issue", entities, email)

    # Should only have 1 contact (sender), recipients without @ are filtered
    assert len(contacts) == 1
    assert contacts[0].email == "anat.siddharth@deeplight.ai"


def test_contact_extraction_mixed_valid_invalid_recipients() -> None:
    """Test with mix of valid emails and name-only recipients."""
    email = EmailRecord(
        id="email-mixed",
        subject="Test",
        sender="alice@example.com",
        recipients=[
            "bob@example.com",  # Valid email
            "Just A Name",  # Invalid - name only
            "Carol White <carol@example.com>",  # Valid - name + email
            "Another Name",  # Invalid - name only
        ],
        date="2025-11-13",
        body_text="Test",
    )

    entities = EntityIndex()
    contacts = _entities_to_contacts("email-mixed", entities, email)

    # Should have 3 contacts: sender + 2 valid recipient emails
    assert len(contacts) == 3

    emails = [c.email for c in contacts]
    assert "alice@example.com" in emails
    assert "bob@example.com" in emails
    assert "carol@example.com" in emails

    # Name-only recipients should NOT be in contacts
    assert "Just A Name" not in emails
    assert "Another Name" not in emails
