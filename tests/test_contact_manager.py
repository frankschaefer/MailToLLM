from __future__ import annotations

from pathlib import Path

from mailtollm.models.schema import ContactExportRecord
from mailtollm.services.contact_manager import ContactManager, write_global_contacts


def test_contact_manager_adds_contacts() -> None:
    manager = ContactManager()
    contacts = [
        ContactExportRecord(
            source="email-1",
            email="test@example.com",
            name="John Doe",
        ),
    ]
    manager.add_contacts(contacts)
    result = manager.get_sorted_contacts()
    assert len(result) == 1
    assert result[0].email == "test@example.com"


def test_contact_manager_deduplicates_by_email() -> None:
    manager = ContactManager()
    contacts = [
        ContactExportRecord(
            source="email-1",
            email="test@example.com",
            name="John",
        ),
        ContactExportRecord(
            source="email-2",
            email="test@example.com",
            name="John Doe",
        ),
    ]
    manager.add_contacts(contacts)
    result = manager.get_sorted_contacts()
    assert len(result) == 1
    # Should prefer longer name
    assert result[0].name == "John Doe"


def test_contact_manager_merges_information() -> None:
    manager = ContactManager()

    # First contact with email and name
    manager.add_contacts([
        ContactExportRecord(
            source="email-1",
            email="test@example.com",
            name="John Doe",
        )
    ])

    # Second contact with same email but adds phone and organization
    manager.add_contacts([
        ContactExportRecord(
            source="email-2",
            email="test@example.com",
            phone="+49 123 456",
            organization="ACME Corp",
        )
    ])

    result = manager.get_sorted_contacts()
    assert len(result) == 1
    assert result[0].email == "test@example.com"
    assert result[0].name == "John Doe"
    assert result[0].phone == "+49 123 456"
    assert result[0].organization == "ACME Corp"


def test_contact_manager_sorts_alphabetically() -> None:
    manager = ContactManager()
    contacts = [
        ContactExportRecord(source="1", email="zebra@example.com"),
        ContactExportRecord(source="2", email="alpha@example.com"),
        ContactExportRecord(source="3", email="beta@example.com"),
    ]
    manager.add_contacts(contacts)
    result = manager.get_sorted_contacts()
    assert result[0].email == "alpha@example.com"
    assert result[1].email == "beta@example.com"
    assert result[2].email == "zebra@example.com"


def test_contact_manager_case_insensitive_dedup() -> None:
    manager = ContactManager()
    contacts = [
        ContactExportRecord(source="1", email="Test@Example.com"),
        ContactExportRecord(source="2", email="test@example.com"),
        ContactExportRecord(source="3", email="TEST@EXAMPLE.COM"),
    ]
    manager.add_contacts(contacts)
    result = manager.get_sorted_contacts()
    assert len(result) == 1


def test_write_global_contacts(tmp_path: Path) -> None:
    contacts = [
        ContactExportRecord(
            source="email-1",
            email="test@example.com",
            name="John Doe",
            organization="ACME",
            phone="+49 123",
            address="Main St 1",
            notes="Test note",
        ),
    ]
    path = tmp_path / "contacts.csv"
    write_global_contacts(path, contacts)

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "test@example.com" in content
    assert "John Doe" in content
    assert "ACME" in content


def test_contact_manager_loads_existing_contacts(tmp_path: Path) -> None:
    # Create existing contacts file
    contacts_path = tmp_path / "contacts.csv"
    contacts_path.write_text(
        "Full Name,Company,Email Address,Business Phone,Business Address,Notes,Source\n"
        "John Doe,ACME,test@example.com,+49 123,Main St,Note,email-1\n",
        encoding="utf-8"
    )

    manager = ContactManager()
    loaded_count = manager.load_existing_contacts(contacts_path)

    assert loaded_count == 1
    result = manager.get_sorted_contacts()
    assert len(result) == 1
    assert result[0].email == "test@example.com"
    assert result[0].name == "John Doe"
    assert result[0].organization == "ACME"


def test_contact_manager_load_returns_zero_if_no_file(tmp_path: Path) -> None:
    """Test that load_existing_contacts returns 0 if file doesn't exist."""
    manager = ContactManager()
    contacts_path = tmp_path / "nonexistent.csv"

    loaded_count = manager.load_existing_contacts(contacts_path)

    assert loaded_count == 0
    assert len(manager.get_sorted_contacts()) == 0
