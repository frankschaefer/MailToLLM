from __future__ import annotations

import csv
from pathlib import Path

from mailtollm.models.schema import ContactExportRecord


class ContactManager:
    """Manages global contact deduplication and merging across all processed emails."""

    def __init__(self) -> None:
        self._contacts_by_email: dict[str, ContactExportRecord] = {}

    def add_contacts(self, contacts: list[ContactExportRecord]) -> None:
        """Add contacts with intelligent merging based on email address."""
        for contact in contacts:
            if not contact.email:
                continue

            email_key = contact.email.lower().strip()

            if email_key in self._contacts_by_email:
                self._merge_contact(email_key, contact)
            else:
                self._contacts_by_email[email_key] = contact

    def _merge_contact(self, email_key: str, new_contact: ContactExportRecord) -> None:
        """Intelligently merge new contact data into existing contact."""
        existing = self._contacts_by_email[email_key]

        # Merge name: prefer longer/more complete name
        if new_contact.name:
            if not existing.name:
                existing.name = new_contact.name
            elif len(new_contact.name) > len(existing.name):
                existing.name = new_contact.name

        # Merge organization: prefer longer/more complete organization
        if new_contact.organization:
            if not existing.organization:
                existing.organization = new_contact.organization
            elif len(new_contact.organization) > len(existing.organization):
                existing.organization = new_contact.organization

        # Merge phone: prefer if existing is empty
        if new_contact.phone and not existing.phone:
            existing.phone = new_contact.phone

        # Merge address: prefer longer/more complete address
        if new_contact.address:
            if not existing.address:
                existing.address = new_contact.address
            elif len(new_contact.address) > len(existing.address):
                existing.address = new_contact.address

        # Merge notes: combine from multiple sources
        if new_contact.notes:
            if existing.notes and new_contact.notes not in existing.notes:
                existing.notes = f"{existing.notes}; {new_contact.notes}"
            elif not existing.notes:
                existing.notes = new_contact.notes

        # Update source to include all sources
        if new_contact.source != existing.source:
            sources = set(existing.source.split("; "))
            sources.add(new_contact.source)
            existing.source = "; ".join(sorted(sources))

    def get_sorted_contacts(self) -> list[ContactExportRecord]:
        """Return all contacts sorted alphabetically by email address."""
        return sorted(
            self._contacts_by_email.values(),
            key=lambda c: c.email.lower() if c.email else ""
        )

    def load_existing_contacts(self, path: Path) -> None:
        """Load existing contacts from CSV file to preserve previous data."""
        if not path.exists():
            return

        try:
            with path.open("r", newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    contact = ContactExportRecord(
                        source=row.get("Source", ""),
                        name=row.get("Full Name") or None,
                        organization=row.get("Company") or None,
                        email=row.get("Email Address") or None,
                        phone=row.get("Business Phone") or None,
                        address=row.get("Business Address") or None,
                        notes=row.get("Notes") or None,
                    )
                    if contact.email:
                        email_key = contact.email.lower().strip()
                        self._contacts_by_email[email_key] = contact
        except Exception:
            # If file is corrupted or format is wrong, start fresh
            pass


def write_global_contacts(path: Path, contacts: list[ContactExportRecord]) -> Path:
    """Write contacts to Outlook-compatible CSV format."""
    path.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "Full Name",
        "Company",
        "Email Address",
        "Business Phone",
        "Business Address",
        "Notes",
        "Source",
    ]

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for contact in contacts:
            writer.writerow([
                contact.name or "",
                contact.organization or "",
                contact.email or "",
                contact.phone or "",
                contact.address or "",
                contact.notes or "",
                contact.source or "",
            ])

    return path
