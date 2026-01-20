from __future__ import annotations

from pathlib import Path

from mailtollm.models.schema import ContactExportRecord
from mailtollm.services.contact_manager import write_global_contacts


def write_outlook_contacts(path: Path, contacts: list[ContactExportRecord]) -> Path:
    """
    Deprecated: Use write_global_contacts from contact_manager instead.
    This function is kept for backwards compatibility.
    """
    return write_global_contacts(path, contacts)
