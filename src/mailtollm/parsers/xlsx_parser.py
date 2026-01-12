from __future__ import annotations

from pathlib import Path

import openpyxl

from mailtollm.models.schema import AttachmentContent


def parse_xlsx(path: Path, attachment_id: str) -> AttachmentContent:
    wb = openpyxl.load_workbook(path, data_only=True)
    tables: list[str] = []
    for sheet in wb.worksheets:
        rows = []
        for row in sheet.iter_rows(values_only=True):
            rows.append(["" if cell is None else str(cell) for cell in row])
        if rows:
            serialized = "\n".join("\t".join(row) for row in rows)
            tables.append(f"Sheet: {sheet.title}\n{serialized}")
    return AttachmentContent(id=attachment_id, text="", tables=tables)
