from __future__ import annotations

import csv
import os
import re
import time
from pathlib import Path
from threading import Event
from typing import Callable

from mailtollm.__version__ import __version__, __version_date__
from mailtollm.io.attachment_resolver import resolve_attachment_paths
from mailtollm.io.csv_reader import read_email_csv
from mailtollm.io.output_writer import read_output_json, write_output_json
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
from mailtollm.services.contact_manager import ContactManager, write_global_contacts
from mailtollm.services.entity_extractor import extract_entities
from mailtollm.services.llm_client import check_llm_available, summarize_text

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, int, int, int, int], None]  # processed, total, contacts, emails, attachments


class LLMConnectionError(Exception):
    """Raised when LLM connection is lost during processing."""
    pass


def _save_contacts(contact_manager: ContactManager, path: Path, on_log: LogCallback | None, verbose: bool = True) -> None:
    """Save contacts to file with optional logging.

    Args:
        contact_manager: The contact manager instance
        path: Path to save contacts file
        on_log: Optional logging callback
        verbose: If True, log detailed information. If False, only save silently.
    """
    sorted_contacts = contact_manager.get_sorted_contacts()
    if sorted_contacts:
        write_global_contacts(path, sorted_contacts)
        if verbose:
            _log(on_log, f"Kontakte gespeichert: {path}")
            _log(on_log, f"Total unique contacts: {len(sorted_contacts)}")


def _is_timeout_error(exc: LLMConnectionError) -> bool:
    """Check if an LLMConnectionError is a timeout that should be retried."""
    error_msg = str(exc).lower()
    # Check for various timeout indicators
    timeout_indicators = [
        "timeout",
        "timed out",
        "timeouterror",
        "urlerror",  # URLError often indicates timeout
        "read timeout",
        "connection timeout",
    ]
    return any(indicator in error_msg for indicator in timeout_indicators)


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
    regenerate_summaries: bool = False,
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

    # Initialize global contact manager
    contact_manager = ContactManager(on_log=on_log)
    global_contacts_path = output_dir / "contacts_outlook.csv"
    loaded_contacts = contact_manager.load_existing_contacts(global_contacts_path)
    if loaded_contacts > 0:
        _log(on_log, f"Loaded {loaded_contacts} existing contacts from {global_contacts_path}")
    else:
        _log(on_log, "No existing contacts file found. Starting fresh.")

    outputs: list[LLMOutput] = []
    processed = 0
    total_emails = 0
    total_attachments = 0

    def progress_hook(emails_in_record: int = 0, attachments_in_record: int = 0) -> None:
        nonlocal processed, total_emails, total_attachments
        processed += 1
        total_emails += emails_in_record
        total_attachments += attachments_in_record
        if on_progress:
            contact_count = len(contact_manager.get_sorted_contacts())
            on_progress(processed, total_records, contact_count, total_emails, total_attachments)
        if on_log and (processed % 50 == 0 or processed == total_records):
            _log(on_log, f"Progress: {processed}/{total_records} | Emails: {total_emails} | Attachments: {total_attachments}")

    for csv_file in csv_files:
        if stop_event and stop_event.is_set():
            _log(on_log, "Stop requested. Exiting pipeline.")
            # Save contacts before stopping
            _save_contacts(contact_manager, global_contacts_path, on_log)
            break
        _wait_if_paused(pause_event, stop_event)

        csv_output_dir = _output_dir_for_csv(csv_path, csv_file, output_dir)
        try:
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
                    regenerate_summaries,
                    contact_manager,
                    global_contacts_path,
                )
            )
            # Save contacts after each CSV file to preserve progress (silently)
            _save_contacts(contact_manager, global_contacts_path, on_log, verbose=False)
        except LLMConnectionError as exc:
            _log(on_log, "")
            _log(on_log, "=" * 80)
            _log(on_log, "FEHLER: LLM Studio Verbindung unterbrochen")
            _log(on_log, "=" * 80)
            _log(on_log, f"Details: {exc}")
            _log(on_log, "")
            _log(on_log, "Die Verarbeitung wurde pausiert.")
            _log(on_log, "")
            _log(on_log, "Bitte beheben Sie das Problem (z.B. LLM Studio neu starten)")
            _log(on_log, "und starten Sie die Verarbeitung erneut.")
            _log(on_log, "")
            _log(on_log, f"Bereits verarbeitete Datensätze: {processed}/{total_records}")
            _log(on_log, "Die Verarbeitung wird beim letzten Datensatz fortgesetzt.")
            _log(on_log, "=" * 80)
            # Save contacts before exiting
            _save_contacts(contact_manager, global_contacts_path, on_log)
            raise
        except Exception as exc:
            _log(on_log, "")
            _log(on_log, "=" * 80)
            _log(on_log, f"FEHLER während der Verarbeitung: {exc}")
            _log(on_log, "=" * 80)
            # Save contacts before exiting
            _save_contacts(contact_manager, global_contacts_path, on_log)
            raise

    # Write global contacts file at the end
    _save_contacts(contact_manager, global_contacts_path, on_log)

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
    on_progress: Callable[[int, int], None] | None,  # (emails, attachments)
    detail_logging: bool,
    regenerate_summaries: bool,
    contact_manager: ContactManager,
    global_contacts_path: Path | None = None,
) -> list[LLMOutput]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = read_email_csv(csv_path, id_prefix=csv_path.stem)

    outputs: list[LLMOutput] = []

    _log(on_log, f"Processing CSV: {csv_path}")

    for record in records:
        if stop_event and stop_event.is_set():
            _log(on_log, "Stop requested. Exiting pipeline.")
            break
        _wait_if_paused(pause_event, stop_event)

        output_path = output_dir / f"{record['id']}.json"
        should_reprocess = False

        # Check if record is worth processing (skip empty calendar entries, etc.)
        if not output_path.exists() and not _is_record_worth_processing(record):
            _log(on_log, f"Skipping {record['id']} (no contacts, attachments, or substantial content)")
            if on_progress:
                # Still count it in progress
                num_attachments = len(record.get("attachment_names", []))
                on_progress(1, num_attachments)
            continue

        if output_path.exists():
            # Check if record needs reprocessing due to LLM errors
            should_reprocess = _should_reprocess_record(output_path, on_log)

            if not should_reprocess:
                if regenerate_summaries and summary_length and summary_length > 0:
                    if _regenerate_summary(
                        output_path,
                        record["id"],
                        summary_length,
                        llm_available,
                        llm_error,
                        on_log,
                        detail_logging,
                    ):
                        if on_progress:
                            # Count emails=1 and attachments from record
                            num_attachments = len(record.get("attachment_names", []))
                            on_progress(1, num_attachments)
                        continue
                _log(on_log, f"Skipping {record['id']} (already processed).")
                if on_progress:
                    # Count emails=1 and attachments from record
                    num_attachments = len(record.get("attachment_names", []))
                    on_progress(1, num_attachments)
                continue
            else:
                _log(on_log, f"Reprocessing {record['id']} due to previous LLM error.")

        _log(on_log, f"Processing {record['id']}")
        _log(on_log, f"Mail preview: {_preview(record['body_text'])}")

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
            _log(on_log, f"Attachment: {path.name}")
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
        contacts_for_email = _entities_to_contacts(record["id"], entities, email)
        contact_manager.add_contacts(contacts_for_email)
        _log_entity_summary(on_log, record["id"], entities, contacts_for_email, detail_logging, email)

        summary_text = ""
        if summary_length and summary_length > 0:
            if llm_available:
                # Retry logic for timeout errors (max 2 retries = 3 total attempts)
                max_retries = 2
                retry_delay = 2.0  # seconds
                last_error = None

                for attempt in range(max_retries + 1):
                    try:
                        if attempt > 0:
                            _log(on_log, f"Wiederhole LLM-Anfrage (Versuch {attempt + 1}/{max_retries + 1})...")
                            time.sleep(retry_delay)

                        (summary_text, summary_warning), summary_elapsed = _time_call(
                            lambda: summarize_text(
                                combined_context,
                                summary_length,
                                file_ext=".email",
                                on_log=on_log,
                                detail_logging=detail_logging,
                            )
                        )
                        if detail_logging:
                            _log(
                                on_log,
                                f"Timing summary ({record['id']}): {summary_elapsed:.2f}s",
                            )
                        if summary_warning:
                            summary_warning.attachment_id = record["id"]
                            warnings.append(summary_warning)
                            # Check if this is a connection error
                            if _is_llm_connection_error(summary_warning):
                                raise LLMConnectionError(
                                    f"LLM connection lost: {summary_warning.details}"
                                )
                        else:
                            _log(on_log, f"Summary preview: {_preview(summary_text)}")

                        # Success - break out of retry loop
                        break

                    except LLMConnectionError as llm_exc:
                        last_error = llm_exc
                        # Log the error for debugging
                        _log(on_log, f"LLM Fehler: {llm_exc}")
                        # Only retry if it's a timeout error and we have retries left
                        if _is_timeout_error(llm_exc) and attempt < max_retries:
                            _log(on_log, f"→ Timeout erkannt, wiederhole in {retry_delay}s...")
                            continue
                        # Either not a timeout or no more retries - re-raise
                        _log(on_log, f"→ Nicht wiederholbar (Timeout={_is_timeout_error(llm_exc)}, Versuche übrig={attempt < max_retries})")
                        raise
                    except Exception as exc:
                        _log(on_log, f"Unexpected error during summary: {exc}")
                        raise LLMConnectionError(f"LLM processing failed: {exc}")
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

        # Save contacts after each email to ensure file is always up-to-date
        if global_contacts_path:
            _save_contacts(contact_manager, global_contacts_path, on_log, verbose=False)

        if on_progress:
            # Count: 1 email and actual number of attachments
            num_attachments = len(attachment_paths)
            on_progress(1, num_attachments)

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


def _preview(text: str, max_len: int = 100) -> str:
    cleaned = " ".join(text.split())
    return cleaned[:max_len]


def _regenerate_summary(
    output_path: Path,
    record_id: str,
    summary_length: int,
    llm_available: bool,
    llm_error: str | None,
    on_log: LogCallback | None,
    detail_logging: bool,
) -> bool:
    try:
        existing = read_output_json(output_path)
    except Exception as exc:
        _log(on_log, f"Failed to read output for {record_id}: {exc}")
        return False

    combined_context = existing.get("combined_context") or ""
    if not combined_context:
        _log(on_log, f"Missing combined_context for {record_id}, reprocessing.")
        return False

    _log(on_log, f"Regenerating summary for {record_id}")
    _log(on_log, f"Mail preview: {_preview(combined_context)}")

    if not llm_available:
        _log(on_log, f"LLM Studio not available: {llm_error}")
        return True

    summary_text, summary_warning = summarize_text(
        combined_context,
        summary_length,
        file_ext=".email",
        on_log=on_log,
        detail_logging=detail_logging,
    )
    if summary_warning:
        _log(on_log, f"Summary failed for {record_id}: {summary_warning.details}")
        return True

    existing["summary_text"] = summary_text
    write_output_json(output_path.parent, LLMOutput.model_validate(existing))
    _log(on_log, f"Summary preview: {_preview(summary_text)}")
    return True


def _log_entity_summary(
    on_log: LogCallback | None,
    record_id: str,
    entities: EntityIndex,
    contacts: list[ContactExportRecord],
    detail_logging: bool,
    email_record: EmailRecord | None = None,
) -> None:
    _log(
        on_log,
        (
            f"Entities ({record_id}): emails={len(entities.emails)}, "
            f"orgs={len(entities.organizations)}, people={len(entities.people)}, "
            f"phones={len(entities.phones)}, addresses={len(entities.addresses)}, "
            f"contacts={len(contacts)}"
        ),
    )

    # Always log sender/recipients info when no contacts are found (debugging)
    if len(contacts) == 0 and email_record:
        sender_info = f"sender='{email_record.sender[:50]}...'" if len(email_record.sender) > 50 else f"sender='{email_record.sender}'"
        recipients_info = f"recipients={len(email_record.recipients)}"
        _log(on_log, f"No contacts extracted! {sender_info}, {recipients_info}")

    if not detail_logging:
        return

    if entities.emails:
        _log(on_log, f"Entity emails: {_format_list(entities.emails)}")
    if entities.organizations:
        _log(on_log, f"Entity orgs: {_format_list(entities.organizations)}")
    if entities.people:
        _log(on_log, f"Entity people: {_format_list(entities.people)}")
    if entities.phones:
        _log(on_log, f"Entity phones: {_format_list(entities.phones)}")
    if entities.addresses:
        _log(on_log, f"Entity addresses: {_format_list(entities.addresses)}")
    if contacts:
        contact_emails = [c.email or "" for c in contacts if c.email]
        if contact_emails:
            _log(on_log, f"Contact emails: {_format_list(contact_emails)}")


def _format_list(values: list[str], limit: int = 20) -> str:
    if len(values) <= limit:
        return ", ".join(values)
    head = ", ".join(values[:limit])
    return f"{head} (+{len(values) - limit} more)"


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


def _extract_email_and_name_from_field(field: str) -> tuple[str | None, str | None]:
    """Extract email address and name from various formats.

    Supports:
    - Plain email: 'alice@example.com' -> (email, None)
    - Name with email: 'Alice Smith <alice@example.com>' -> (email, 'Alice Smith')
    - Name only: 'Alice Smith' -> (None, None)

    Returns (email, name) tuple. Both can be None.
    """
    if not field:
        return (None, None)

    field = field.strip()

    # Check for "Name <email>" format
    match = re.search(r'^(.+?)\s*<([^>]+@[^>]+)>$', field)
    if match:
        name = match.group(1).strip()
        email = match.group(2).strip()
        return (email, name)

    # Check if it's a plain email (contains @)
    if '@' in field and ' ' not in field:
        return (field, None)

    # It's just a name, no email
    return (None, None)


def _extract_email_from_field(field: str) -> str | None:
    """Extract email address from various formats (backward compatibility)."""
    email, _ = _extract_email_and_name_from_field(field)
    return email


def _guess_name_from_email(email: str) -> str | None:
    """Attempt to extract a name from an email address.

    Examples:
    - john.doe@example.com -> John Doe
    - j.smith@example.com -> J Smith
    - alice-wonderland@example.com -> Alice Wonderland
    - info@company.com -> None (generic email)

    Returns None if email appears to be generic/role-based.
    """
    if not email or '@' not in email:
        return None

    local_part = email.split('@')[0].lower()

    # Skip generic/role-based emails
    generic_prefixes = ['info', 'admin', 'support', 'contact', 'hello', 'sales',
                       'noreply', 'no-reply', 'postmaster', 'webmaster', 'office']
    if local_part in generic_prefixes:
        return None

    # Replace common separators with spaces
    name_parts = re.split(r'[._-]', local_part)

    # Skip if too many parts (likely not a person name)
    if len(name_parts) > 4:
        return None

    # Capitalize each part
    capitalized = [part.capitalize() for part in name_parts if part]

    if not capitalized:
        return None

    return ' '.join(capitalized)


def _entities_to_contacts(source_id: str, entities: EntityIndex, email_record: EmailRecord) -> list[ContactExportRecord]:
    contacts: list[ContactExportRecord] = []
    processed_emails: set[str] = set()

    # Add sender contact
    sender_email, sender_name = _extract_email_and_name_from_field(email_record.sender)
    if sender_email:
        # If no name from field, try to guess from email address
        if not sender_name:
            sender_name = _guess_name_from_email(sender_email)

        contacts.append(
            ContactExportRecord(
                source=source_id,
                email=sender_email,
                name=sender_name,
                organization=entities.organizations[0] if entities.organizations else None,
                notes="Email sender",
            )
        )
        processed_emails.add(sender_email.lower())
    # Debug: If no sender email was extracted, it means the field was empty or invalid
    # This will be caught by _log_entity_summary showing sender field content

    # Add recipient contacts
    for recipient in email_record.recipients:
        recipient_email, recipient_name = _extract_email_and_name_from_field(recipient)
        if recipient_email and recipient_email.lower() not in processed_emails:
            # If no name from field, try to guess from email address
            if not recipient_name:
                recipient_name = _guess_name_from_email(recipient_email)

            contacts.append(
                ContactExportRecord(
                    source=source_id,
                    email=recipient_email,
                    name=recipient_name,
                    organization=entities.organizations[0] if entities.organizations else None,
                    notes="Email recipient",
                )
            )
            processed_emails.add(recipient_email.lower())

    # Add contacts from extracted entities in body/attachments
    for email in entities.emails:
        if email.lower() not in processed_emails:
            # Try to guess name from email address
            guessed_name = _guess_name_from_email(email)

            contacts.append(
                ContactExportRecord(
                    source=source_id,
                    email=email,
                    name=guessed_name,
                    organization=entities.organizations[0] if entities.organizations else None,
                    phone=entities.phones[0] if entities.phones else None,
                    address=entities.addresses[0] if entities.addresses else None,
                    notes="Auto extracted from content",
                )
            )
            processed_emails.add(email.lower())

    return contacts


def _is_record_worth_processing(record: dict) -> bool:
    """Check if a record contains useful information worth processing.

    Skip records that have:
    - No sender/recipients (empty contact fields)
    - No attachments
    - Very short body text (< 50 chars) - likely just calendar entries

    Returns True if record should be processed, False if it should be skipped.
    """
    # Check for sender or recipients (handle None values)
    sender = record.get("sender") or ""
    recipients = record.get("recipients") or []
    has_contacts = bool(sender.strip()) or bool(recipients)

    # Check for attachments
    has_attachments = bool(record.get("attachment_names"))

    # Check for substantial body content (handle None values)
    body_text = (record.get("body_text") or "").strip()
    body_html = (record.get("body_html") or "").strip()
    has_content = len(body_text) >= 50 or len(body_html) >= 100

    # Process if any of these conditions are met
    return has_contacts or has_attachments or has_content


def _should_reprocess_record(output_path: Path, on_log: LogCallback | None) -> bool:
    """Check if a record should be reprocessed due to previous LLM errors."""
    try:
        existing = read_output_json(output_path)
        warnings = existing.get("warnings", [])

        for warning in warnings:
            details = warning.get("details", "")
            code = warning.get("code", "")
            if not details:
                continue

            # Skip context overflow errors - these are not recoverable without truncation
            if "context" in details.lower() and "overflow" in details.lower():
                continue
            if "tokens" in details.lower() and ("4096" in details or "overflows" in details):
                continue

            # Check for recoverable LLM errors
            if "HTTP Error 400" in details or "Bad Request" in details:
                return True
            if "HTTP Error 500" in details or "Internal Server Error" in details:
                return True
            if "Connection refused" in details or "Connection reset" in details:
                return True
            if "timeout" in details.lower():
                return True
            if code in ("LLM_CONNECTION_ERROR", "LLM_HTTP_ERROR"):
                return True

        return False
    except Exception:
        return False


def _is_llm_connection_error(warning: WarningRecord) -> bool:
    """Check if a warning indicates a critical LLM connection error that should stop processing."""
    if not warning.details:
        return False

    # Don't treat context overflow as connection error - it's a data issue, not connection issue
    details_lower = warning.details.lower()
    if "context" in details_lower and "overflow" in details_lower:
        return False
    if "tokens" in details_lower and ("4096" in warning.details or "overflows" in details_lower):
        return False

    # Critical connection errors
    error_indicators = [
        "HTTP Error 500",
        "Internal Server Error",
        "Connection refused",
        "Connection reset",
        "Channel Error",
        "timed out",
    ]

    # Check error codes
    if warning.code in ("LLM_CONNECTION_ERROR", "LLM_UNAVAILABLE"):
        return True

    details = warning.details
    return any(indicator in details for indicator in error_indicators)


def _wait_if_paused(pause_event: Event | None, stop_event: Event | None) -> None:
    while pause_event and pause_event.is_set():
        if stop_event and stop_event.is_set():
            return
        time.sleep(0.2)


def _log(on_log: LogCallback | None, message: str) -> None:
    if on_log:
        on_log(message)
