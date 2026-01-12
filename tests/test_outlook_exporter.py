from pathlib import Path
import csv

from mailtollm.models.schema import ContactExportRecord
from mailtollm.services.outlook_exporter import write_outlook_contacts


def test_write_outlook_contacts(tmp_path: Path) -> None:
    contacts = [
        ContactExportRecord(
            source="email-1",
            name="Jane Doe",
            organization="ACME GmbH",
            email="jane@acme.de",
            phone="+49 30 123456",
            address="Mainstrasse 12, 12345 Berlin",
            notes="Auto extracted",
        )
    ]

    path = write_outlook_contacts(tmp_path / "contacts.csv", contacts)

    with path.open("r", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows[0] == [
        "Full Name",
        "Company",
        "Email Address",
        "Business Phone",
        "Business Address",
        "Notes",
    ]
    assert rows[1][0] == "Jane Doe"
    assert rows[1][2] == "jane@acme.de"
