from __future__ import annotations

import csv
import os
import time
from pathlib import Path
from threading import Event
from typing import Callable

from mailtollm.io.attachment_resolver import resolve_attachment_paths
from mailtollm.io.csv_reader import read_email_csv
from mailtollm.io.output_writer import write_output_json
from mailtollm.models.schema import (
    AttachmentContent,
    AttachmentMeta,
    ContactExportRecord,
    EmailRecord,
    EntityIndex,
    LLMOutput,
    WarningRecord,
)
from mailtollm.parsers.docx_parser import parse_docx
from mailtollm.parsers.image_parser import parse_image
from mailtollm.parsers.pdf_parser import parse_pdf
from mailtollm.parsers.pptx_parser import parse_pptx
from mailtollm.parsers.text_parser import parse_text
from mailtollm.parsers.xlsx_parser import parse_xlsx
from mailtollm.services.entity_extractor import extract_entities
from mailtollm.services.llm_client import check_llm_available, summarize_text
from mailtollm.services.outlook_exporter import write_outlook_contacts

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, int], None]


def run_pipeline(
    csv_path: Path,
    attachments_root: Path,
    output_dir: Path,
    summary_length: int | None = None,
    pause_event: Event | None = None,
    stop_event: Event | None = None,
    on_log: LogCallback | None = None,
    on_progress: ProgressCallback | None = None,
    detail_logging: bool = False,
) -> list[LLMOutput]:
    output_dir.mkdir(parents=True, exist_ok=True)

    llm_available = True
    llm_error: str | None = None
    if summary_length and summary_length > 0:
        llm_available, llm_error = check_llm_available(
            os.environ.get("LLM_STUDIO_URL", "http://localhost:1234/v1/chat/completions")
        )
        if not llm_available:
            _log(on_log, f"LLM Studio not available: {llm_error}")

    scan_start = time.perf_counter()
    csv_files = _collect_csv_files(csv_path)
    if not csv_files:
        _log(on_log, "No CSV files found.")
        return []

    total_records = _count_total_records(csv_files)
    scan_elapsed = time.perf_counter() - scan_start
    if detail_logging:
        _log(on_log, f"Timing scan: {scan_elapsed:.2f}s")
    if total_records:
        _log(on_log, f"Scan complete: {len(csv_files)} CSV files, {total_records} emails.")
    else:
        _log(on_log, f"Scan complete: {len(csv_files)} CSV files, no emails found.")

    outputs: list[LLMOutput] = []
    processed = 0

    def progress_hook() -> None:
        nonlocal processed
        processed += 1
        if on_progress:
            on_progress(processed, total_records)
        if on_log and (processed % 50 == 0 or processed == total_records):
            _log(on_log, f"Progress: {processed}/{total_records}")

    for csv_file in csv_files:
        if stop_event and stop_event.is_set():
            _log(on_log, "Stop requested. Exiting pipeline.")
            break
        _wait_if_paused(pause_event, stop_event)

        csv_output_dir = _output_dir_for_csv(csv_path, csv_file, output_dir)
        outputs.extend(
            _run_single_csv(
                csv_file,
                attachments_root,
                csv_output_dir,
                summary_length,
                pause_event,
                stop_event,
                on_log,
                llm_available,
                llm_error,
                progress_hook,
                detail_logging,
            )
        )

    return outputs


def _run_single_csv(
    csv_path: Path,
    attachments_root: Path,
    output_dir: Path,
    summary_length: int | None,
    pause_event: Event | None,
    stop_event: Event | None,
    on_log: LogCallback | None,
    llm_available: bool,
    llm_error: str | None,
    on_progress: Callable[[], None] | None,
    detail_logging: bool,
) -> list[LLMOutput]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = read_email_csv(csv_path, id_prefix=csv_path.stem)

    outputs: list[LLMOutput] = []
    contacts: list[ContactExportRecord] = []

    _log(on_log, f"Processing CSV: {csv_path}")

    for record in records:
        if stop_event and stop_event.is_set():
            _log(on_log, "Stop requested. Exiting pipeline.")
            break
        _wait_if_paused(pause_event, stop_event)

        output_path = output_dir / f"{record['id']}.json"
        if output_path.exists():
            _log(on_log, f"Skipping {record['id']} (already processed).")
            if on_progress:
                on_progress()
            continue

        _log(on_log, f"Processing {record['id']}")

        email = EmailRecord(
            id=record["id"],
            subject=record["subject"],
            sender=record["sender"],
            recipients=record["recipients"],
            date=record["date"],
            body_text=record["body_text"],
            body_html=record["body_html"],
        )

        attachment_paths, resolve_elapsed = _time_call(
            lambda: resolve_attachment_paths(
                attachments_root,
                record["folder"],
                record["attachment_names"],
            )
        )
        if detail_logging:
            _log(on_log, f"Timing resolve attachments ({record['id']}): {resolve_elapsed:.2f}s")

        attachment_contents: list[AttachmentContent] = []
        warnings: list[WarningRecord] = []
        attachments: list[AttachmentMeta] = []

        for idx, path in enumerate(attachment_paths, start=1):
            if stop_event and stop_event.is_set():
                _log(on_log, "Stop requested during attachments.")
                break
            _wait_if_paused(pause_event, stop_event)

            attachment_id = f"{record['id']}-att-{idx}"
            attachments.append(
                AttachmentMeta(
                    id=attachment_id,
                    filename=path.name,
                    path=str(path),
                    mime_type=path.suffix.lower().lstrip(".") or "unknown",
                    size_bytes=path.stat().st_size,
                )
            )
            (content, content_warnings), parse_elapsed = _time_call(
                lambda: _parse_attachment(path, attachment_id)
            )
            if detail_logging:
                _log(
                    on_log,
                    f"Timing parse {path.name} ({record['id']}): {parse_elapsed:.2f}s",
                )
            attachment_contents.append(content)
            warnings.extend(content_warnings)

        email.attachments = attachments

        combined_context, context_elapsed = _time_call(
            lambda: _build_context(email, attachment_contents)
        )
        entities, entity_elapsed = _time_call(lambda: extract_entities(combined_context))
        if detail_logging:
            _log(on_log, f"Timing build context ({record['id']}): {context_elapsed:.2f}s")
            _log(on_log, f"Timing entity extract ({record['id']}): {entity_elapsed:.2f}s")
        contacts_for_email = _entities_to_contacts(record["id"], entities)
        contacts.extend(contacts_for_email)

        summary_text = ""
        if summary_length and summary_length > 0:
            if llm_available:
                (summary_text, summary_warning), summary_elapsed = _time_call(
                    lambda: summarize_text(combined_context, summary_length)
                )
                if detail_logging:
                    _log(
                        on_log,
                        f"Timing summary ({record['id']}): {summary_elapsed:.2f}s",
                    )
                if summary_warning:
                    summary_warning.attachment_id = record["id"]
                    warnings.append(summary_warning)
            else:
                warnings.append(
                    WarningRecord(
                        attachment_id=record["id"],
                        code="LLM_UNAVAILABLE",
                        message="LLM Studio nicht verfuegbar",
                        details=llm_error,
                    )
                )

        output = LLMOutput(
            email=email,
            warnings=warnings,
            attachment_contents=attachment_contents,
            entities=entities,
            contacts_export=contacts_for_email,
            summary_text=summary_text,
            combined_context=combined_context,
        )
        _, write_elapsed = _time_call(lambda: write_output_json(output_dir, output))
        if detail_logging:
            _log(on_log, f"Timing write output ({record['id']}): {write_elapsed:.2f}s")
        outputs.append(output)
        if on_progress:
            on_progress()

    if contacts:
        unique_contacts = _dedupe_contacts(contacts)
        write_outlook_contacts(output_dir / "contacts_outlook.csv", unique_contacts)

    return outputs


def _parse_attachment(path: Path, attachment_id: str) -> tuple[AttachmentContent, list[WarningRecord]]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            return parse_pdf(path, attachment_id)
        if suffix in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
            return parse_image(path, attachment_id)
        if suffix == ".docx":
            return parse_docx(path, attachment_id), []
        if suffix == ".pptx":
            return parse_pptx(path, attachment_id), []
        if suffix == ".xlsx":
            return parse_xlsx(path, attachment_id), []
        if suffix in {".txt", ".md"}:
            return parse_text(path, attachment_id), []
    except Exception as exc:
        return (
            AttachmentContent(id=attachment_id),
            [
                WarningRecord(
                    attachment_id=attachment_id,
                    code="PARSE_ERROR",
                    message="Nicht lesbar",
                    details=str(exc),
                )
            ],
        )

    return AttachmentContent(id=attachment_id), []


def _collect_csv_files(csv_path: Path) -> list[Path]:
    if csv_path.is_dir():
        return sorted(csv_path.rglob("*.csv"))
    if csv_path.is_file():
        return [csv_path]
    return []


def _output_dir_for_csv(input_root: Path, csv_path: Path, output_root: Path) -> Path:
    if input_root.is_file():
        return output_root
    try:
        relative = csv_path.parent.relative_to(input_root)
    except ValueError:
        return output_root
    filtered_parts = [part for part in relative.parts if part.lower() != "attachments"]
    if not filtered_parts:
        return output_root
    return output_root.joinpath(*filtered_parts)


def _count_total_records(csv_files: list[Path]) -> int:
    total = 0
    for csv_file in csv_files:
        total += _count_csv_records(csv_file)
    return total


def _count_csv_records(csv_path: Path) -> int:
    try:
        with csv_path.open(newline="", encoding="utf-8", errors="replace") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            return sum(1 for _ in reader)
    except Exception:
        return 0


def _time_call(func: Callable[[], object]) -> tuple[object, float]:
    start = time.perf_counter()
    result = func()
    return result, time.perf_counter() - start


def _build_context(email: EmailRecord, attachments: list[AttachmentContent]) -> str:
    header = (
        f"From: {email.sender}\n"
        f"To: {', '.join(email.recipients)}\n"
        f"Date: {email.date}\n"
        f"Subject: {email.subject}"
    )
    body = email.body_text.strip()
    parts = [header, "", body]

    for attachment in attachments:
        section = [f"Attachment {attachment.id}:"]
        if attachment.text:
            section.append(attachment.text)
        if attachment.tables:
            section.append("\n".join(attachment.tables))
        if attachment.ocr_text:
            section.append(attachment.ocr_text)
        parts.append("\n".join(section))

    return "\n\n".join(part for part in parts if part.strip())


def _entities_to_contacts(source_id: str, entities: EntityIndex) -> list[ContactExportRecord]:
    contacts: list[ContactExportRecord] = []
    for email in entities.emails:
        contacts.append(
            ContactExportRecord(
                source=source_id,
                email=email,
                organization=entities.organizations[0] if entities.organizations else None,
                phone=entities.phones[0] if entities.phones else None,
                address=entities.addresses[0] if entities.addresses else None,
                notes="Auto extracted",
            )
        )
    return contacts


def _dedupe_contacts(contacts: list[ContactExportRecord]) -> list[ContactExportRecord]:
    seen: set[tuple[str | None, str | None, str | None, str | None]] = set()
    unique: list[ContactExportRecord] = []
    for contact in contacts:
        key = (contact.email, contact.organization, contact.phone, contact.address)
        if key in seen:
            continue
        seen.add(key)
        unique.append(contact)
    return unique


def _wait_if_paused(pause_event: Event | None, stop_event: Event | None) -> None:
    while pause_event and pause_event.is_set():
        if stop_event and stop_event.is_set():
            return
        time.sleep(0.2)


def _log(on_log: LogCallback | None, message: str) -> None:
    if on_log:
        on_log(message)
