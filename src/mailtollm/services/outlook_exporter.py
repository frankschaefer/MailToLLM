from __future__ import annotations

import csv
from pathlib import Path

from mailtollm.models.schema import ContactExportRecord

OUTLOOK_HEADERS = [
    "Full Name",
    "Company",
    "Email Address",
    "Business Phone",
    "Business Address",
    "Notes",
]


def write_outlook_contacts(path: Path, contacts: list[ContactExportRecord]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(OUTLOOK_HEADERS)
        for contact in contacts:
            writer.writerow(
                [
                    contact.name or "",
                    contact.organization or "",
                    contact.email or "",
                    contact.phone or "",
                    contact.address or "",
                    contact.notes or "",
                ]
            )
    return path
