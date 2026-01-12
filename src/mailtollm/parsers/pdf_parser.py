from __future__ import annotations

from pathlib import Path
import pdfplumber

from mailtollm.models.schema import AttachmentContent, WarningRecord
from mailtollm.services.ocr import ocr_image


def _contains_javascript(raw_bytes: bytes) -> bool:
    return b"/JavaScript" in raw_bytes or b"/JS" in raw_bytes


def parse_pdf(path: Path, attachment_id: str) -> tuple[AttachmentContent, list[WarningRecord]]:
    warnings: list[WarningRecord] = []
    text_parts: list[str] = []
    tables: list[str] = []
    ocr_parts: list[str] = []

    raw_bytes = path.read_bytes()
    if _contains_javascript(raw_bytes):
        warnings.append(
            WarningRecord(
                attachment_id=attachment_id,
                code="UNREADABLE",
                message="Nicht lesbar",
                details="PDF contains JavaScript actions.",
            )
        )
        return AttachmentContent(id=attachment_id), warnings

    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text:
                    text_parts.append(page_text)
                else:
                    image = page.to_image(resolution=200).original
                    ocr_text, ocr_warning = ocr_image(image, attachment_id)
                    if ocr_warning:
                        warnings.append(ocr_warning)
                    if ocr_text:
                        ocr_parts.append(ocr_text)
                for table in page.extract_tables():
                    serialized = "\n".join("\t".join(cell or "" for cell in row) for row in table)
                    if serialized.strip():
                        tables.append(serialized)

            combined_text = "\n\n".join(text_parts).strip()
            combined_ocr = "\n\n".join(ocr_parts).strip()

            return (
                AttachmentContent(
                    id=attachment_id,
                    text=combined_text,
                    tables=tables,
                    ocr_text=combined_ocr,
                ),
                warnings,
            )
    except Exception as exc:  # pdfplumber raises on encrypted/unsupported PDFs
        warnings.append(
            WarningRecord(
                attachment_id=attachment_id,
                code="UNREADABLE",
                message="Nicht lesbar",
                details=str(exc),
            )
        )
        return AttachmentContent(id=attachment_id), warnings

