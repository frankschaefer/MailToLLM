from __future__ import annotations

from pathlib import Path

from PIL import Image

from mailtollm.models.schema import AttachmentContent, WarningRecord
from mailtollm.services.ocr import ocr_image


def parse_image(path: Path, attachment_id: str) -> tuple[AttachmentContent, list[WarningRecord]]:
    warnings: list[WarningRecord] = []
    with Image.open(path) as image:
        ocr_text, ocr_warning = ocr_image(image, attachment_id)
        if ocr_warning:
            warnings.append(ocr_warning)
    return AttachmentContent(id=attachment_id, text="", tables=[], ocr_text=ocr_text), warnings
