from __future__ import annotations

from pathlib import Path

from mailtollm.models.schema import AttachmentContent


def parse_text(path: Path, attachment_id: str) -> AttachmentContent:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return AttachmentContent(id=attachment_id, text=text.strip())
