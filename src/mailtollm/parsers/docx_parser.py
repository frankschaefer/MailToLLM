from __future__ import annotations

from pathlib import Path

from docx import Document

from mailtollm.models.schema import AttachmentContent


def parse_docx(path: Path, attachment_id: str) -> AttachmentContent:
    doc = Document(path)
    text_parts = [p.text for p in doc.paragraphs if p.text.strip()]
    return AttachmentContent(id=attachment_id, text="\n".join(text_parts).strip())
