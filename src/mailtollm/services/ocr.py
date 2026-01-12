from __future__ import annotations

from typing import Any

from mailtollm.models.schema import WarningRecord


def _load_tesseract() -> tuple[Any | None, str | None]:
    try:
        import pytesseract  # type: ignore

        try:
            pytesseract.get_tesseract_version()
        except Exception as exc:
            return None, f"tesseract not available: {exc}"

        return pytesseract, None
    except Exception:
        return None, "pytesseract not installed"


def ocr_image(image: Any, attachment_id: str) -> tuple[str, WarningRecord | None]:
    pytesseract, error = _load_tesseract()
    if not pytesseract:
        return (
            "",
            WarningRecord(
                attachment_id=attachment_id,
                code="OCR_NOT_AVAILABLE",
                message="OCR nicht verfuegbar",
                details=error,
            ),
        )
    try:
        text = pytesseract.image_to_string(image)
        return text.strip(), None
    except Exception as exc:
        return (
            "",
            WarningRecord(
                attachment_id=attachment_id,
                code="OCR_ERROR",
                message="OCR fehlgeschlagen",
                details=str(exc),
            ),
        )
