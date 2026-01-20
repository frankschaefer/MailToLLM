from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

from mailtollm.models.schema import ContactExportRecord

LogCallback = Callable[[str], None]


class ContactManager:
    """Manages global contact deduplication and merging across all processed emails."""

    def __init__(self, on_log: LogCallback | None = None) -> None:
        self._contacts_by_email: dict[str, ContactExportRecord] = {}
        self._on_log = on_log

    def add_contacts(self, contacts: list[ContactExportRecord], source_id: str = "") -> list[str]:
        """
        Add contacts with intelligent merging based on email address.

        Returns a list of log messages describing what happened.
        """
        log_messages: list[str] = []

        for contact in contacts:
            if not contact.email:
                continue

            email_key = contact.email.lower().strip()

            if email_key in self._contacts_by_email:
                merge_info = self._merge_contact(email_key, contact)
                if merge_info:
                    msg = f"  Contact updated: {contact.email} - {merge_info}"
                    log_messages.append(msg)
                    if self._on_log:
                        self._on_log(msg)
                else:
                    msg = f"  Contact duplicate (no new info): {contact.email}"
                    log_messages.append(msg)
                    if self._on_log:
                        self._on_log(msg)
            else:
                self._contacts_by_email[email_key] = contact
                name_part = f" ({contact.name})" if contact.name else ""
                org_part = f" - {contact.organization}" if contact.organization else ""
                msg = f"  New contact: {contact.email}{name_part}{org_part}"
                log_messages.append(msg)
                if self._on_log:
                    self._on_log(msg)

        return log_messages

    def _merge_contact(self, email_key: str, new_contact: ContactExportRecord) -> str | None:
        """Intelligently merge new contact data into existing contact.

        Returns a description of what was merged, or None if nothing changed.
        """
        existing = self._contacts_by_email[email_key]
        changes: list[str] = []

        # Merge name: prefer longer/more complete name
        if new_contact.name:
            if not existing.name:
                existing.name = new_contact.name
                changes.append(f"added name '{new_contact.name}'")
            elif len(new_contact.name) > len(existing.name):
                old_name = existing.name
                existing.name = new_contact.name
                changes.append(f"updated name from '{old_name}' to '{new_contact.name}'")

        # Merge organization: prefer longer/more complete organization
        if new_contact.organization:
            if not existing.organization:
                existing.organization = new_contact.organization
                changes.append(f"added organization '{new_contact.organization}'")
            elif len(new_contact.organization) > len(existing.organization):
                old_org = existing.organization
                existing.organization = new_contact.organization
                changes.append(f"updated organization from '{old_org}' to '{new_contact.organization}'")

        # Merge phone: prefer if existing is empty
        if new_contact.phone and not existing.phone:
            existing.phone = new_contact.phone
            changes.append(f"added phone '{new_contact.phone}'")

        # Merge address: prefer longer/more complete address
        if new_contact.address:
            if not existing.address:
                existing.address = new_contact.address
                changes.append(f"added address '{new_contact.address}'")
            elif len(new_contact.address) > len(existing.address):
                old_addr = existing.address
                existing.address = new_contact.address
                changes.append(f"updated address from '{old_addr}' to '{new_contact.address}'")

        # Merge notes: combine from multiple sources
        if new_contact.notes:
            if existing.notes and new_contact.notes not in existing.notes:
                existing.notes = f"{existing.notes}; {new_contact.notes}"
                changes.append(f"added notes '{new_contact.notes}'")
            elif not existing.notes:
                existing.notes = new_contact.notes
                changes.append(f"added notes '{new_contact.notes}'")

        # Update source to include all sources
        if new_contact.source != existing.source:
            sources = set(existing.source.split("; "))
            sources.add(new_contact.source)
            existing.source = "; ".join(sorted(sources))
            changes.append(f"added source '{new_contact.source}'")

        if changes:
            return ", ".join(changes)
        return None

    def get_sorted_contacts(self) -> list[ContactExportRecord]:
        """Return all contacts sorted alphabetically by email address."""
        return sorted(
            self._contacts_by_email.values(),
            key=lambda c: c.email.lower() if c.email else ""
        )

    def load_existing_contacts(self, path: Path) -> int:
        """Load existing contacts from CSV file to preserve previous data.

        Returns the number of contacts loaded.
        """
        if not path.exists():
            return 0

        loaded_count = 0
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
                        loaded_count += 1
        except Exception:
            # If file is corrupted or format is wrong, start fresh
            pass

        return loaded_count


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
