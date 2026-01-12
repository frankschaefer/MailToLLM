from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def _clean_header(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("\ufeff"):
        cleaned = cleaned.replace("\ufeff", "", 1)
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) > 1:
        cleaned = cleaned[1:-1]
    return cleaned.strip()


def _normalize_columns(columns: list[str]) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for idx, name in enumerate(columns):
        normalized[name.lower().strip()] = idx
    return normalized


def _pick_column(columns: dict[str, int], candidates: list[str]) -> int | None:
    for candidate in candidates:
        key = candidate.lower()
        if key in columns:
            return columns[key]
    return None


def _split_list(value: Any) -> list[str]:
    if value is None:
        return []
    text = str(value)
    if not text.strip():
        return []
    parts = [p.strip() for p in text.replace(";", ",").split(",")]
    return [p for p in parts if p]


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _combine_name_address(name: str, address: str) -> str:
    if name and address:
        return f"{name} <{address}>"
    return address or name


def _combine_name_address_lists(names: list[str], addresses: list[str]) -> list[str]:
    if not names and not addresses:
        return []
    if names and addresses and len(names) == len(addresses):
        return [f"{n} <{a}>" for n, a in zip(names, addresses)]
    combined = []
    for idx, name in enumerate(names):
        if idx < len(addresses):
            combined.append(f"{name} <{addresses[idx]}>")
        else:
            combined.append(name)
    for address in addresses[len(names) :]:
        combined.append(address)
    return combined


def _dedupe_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _align_row(row: list[str], size: int) -> list[str]:
    if len(row) < size:
        return row + [""] * (size - len(row))
    if len(row) > size:
        return row[:size]
    return row


def read_email_csv(csv_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    with csv_path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.reader(handle)
        header_raw = next(reader)
        headers = [_clean_header(h) for h in header_raw]
        columns = _normalize_columns(headers)

        id_col = _pick_column(columns, ["id", "message_id", "email_id"])
        subject_col = _pick_column(columns, ["subject", "betreff"])
        sender_col = _pick_column(
            columns, ["from:", "from", "sender", "absender", "from: (address)"]
        )
        sender_name_col = _pick_column(columns, ["from: (name)", "from name", "sender name"])
        sender_addr_col = _pick_column(
            columns, ["from: (address)", "from address", "sender address"]
        )
        recipients_col = _pick_column(columns, ["to:", "to", "recipients", "empfaenger", "an"])
        to_name_col = _pick_column(columns, ["to: (name)", "to name"])
        to_addr_col = _pick_column(columns, ["to: (address)", "to address"])
        cc_col = _pick_column(columns, ["cc:", "cc", "cc: (address)", "cc address"])
        bcc_col = _pick_column(columns, ["bcc", "bcc: (address)", "bcc address"])
        date_col = _pick_column(
            columns, ["date", "datum", "sent", "sent_on", "time", "received", "received on"]
        )
        body_col = _pick_column(
            columns, ["body", "body_text", "text", "inhalt", "message", "content"]
        )
        html_col = _pick_column(columns, ["body_html", "html", "bodyhtml"])
        attachments_col = _pick_column(
            columns,
            [
                "attachments:",
                "attachments",
                "attachment",
                "attachment names",
                "files",
                "dateien",
                "attachment name",
            ],
        )
        folder_col = _pick_column(
            columns, ["attachments path:", "folder", "directory", "path", "ordner", "folder path"]
        )

        for idx, row in enumerate(reader):
            row = _align_row(row, len(headers))
            record_id = _safe_str(row[id_col]) if id_col is not None else f"row-{idx+1}"

            sender = ""
            if sender_name_col is not None or sender_addr_col is not None:
                sender = _combine_name_address(
                    _safe_str(row[sender_name_col]) if sender_name_col is not None else "",
                    _safe_str(row[sender_addr_col]) if sender_addr_col is not None else "",
                )
            if not sender and sender_col is not None:
                sender = _safe_str(row[sender_col])

            recipients: list[str] = []
            if recipients_col is not None:
                recipients.extend(_split_list(row[recipients_col]))
            if to_name_col is not None or to_addr_col is not None:
                recipients.extend(
                    _combine_name_address_lists(
                        _split_list(row[to_name_col]) if to_name_col is not None else [],
                        _split_list(row[to_addr_col]) if to_addr_col is not None else [],
                    )
                )
            if cc_col is not None:
                recipients.extend(_split_list(row[cc_col]))
            if bcc_col is not None:
                recipients.extend(_split_list(row[bcc_col]))

            records.append(
                {
                    "id": record_id,
                    "subject": _safe_str(row[subject_col]) if subject_col is not None else "",
                    "sender": sender,
                    "recipients": _dedupe_list([r for r in recipients if r]),
                    "date": _safe_str(row[date_col]) if date_col is not None else "",
                    "body_text": _safe_str(row[body_col]) if body_col is not None else "",
                    "body_html": _safe_str(row[html_col]) if html_col is not None else None,
                    "attachment_names": _split_list(row[attachments_col])
                    if attachments_col is not None
                    else [],
                    "folder": _safe_str(row[folder_col]) if folder_col is not None else "",
                }
            )

    return records
