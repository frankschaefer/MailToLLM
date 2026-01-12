from __future__ import annotations

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


def run_pipeline(
    csv_path: Path,
    attachments_root: Path,
    output_dir: Path,
    summary_length: int | None = None,
    pause_event: Event | None = None,
    stop_event: Event | None = None,
    on_log: LogCallback | None = None,
) -> list[LLMOutput]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = read_email_csv(csv_path)

    outputs: list[LLMOutput] = []
    contacts: list[ContactExportRecord] = []

    llm_available = True
    llm_error: str | None = None
    if summary_length and summary_length > 0:
        llm_available, llm_error = check_llm_available(
            os.environ.get("LLM_STUDIO_URL", "http://localhost:1234/v1/chat/completions")
        )
        if not llm_available:
            _log(on_log, f"LLM Studio not available: {llm_error}")

    for record in records:
        if stop_event and stop_event.is_set():
            _log(on_log, "Stop requested. Exiting pipeline.")
            break
        _wait_if_paused(pause_event, stop_event)

        output_path = output_dir / f"{record['id']}.json"
        if output_path.exists():
            _log(on_log, f"Skipping {record['id']} (already processed).")
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

        attachment_paths = resolve_attachment_paths(
            attachments_root,
            record["folder"],
            record["attachment_names"],
        )

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
            content, content_warnings = _parse_attachment(path, attachment_id)
            attachment_contents.append(content)
            warnings.extend(content_warnings)

        email.attachments = attachments

        combined_context = _build_context(email, attachment_contents)
        entities = extract_entities(combined_context)
        contacts_for_email = _entities_to_contacts(record["id"], entities)
        contacts.extend(contacts_for_email)

        summary_text = ""
        if summary_length and summary_length > 0:
            if llm_available:
                summary_text, summary_warning = summarize_text(combined_context, summary_length)
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
        write_output_json(output_dir, output)
        outputs.append(output)

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
